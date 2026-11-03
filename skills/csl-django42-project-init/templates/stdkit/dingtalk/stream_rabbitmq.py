import pika
from pika.exceptions import AMQPConnectionError
import json
import time
import dingtalk_stream
from dingtalk_stream.frames import EventMessage
from django.conf import settings
import logging

logger = logging.getLogger("django")


class Publisher(dingtalk_stream.EventHandler):
    async def process(self, event: dingtalk_stream.EventMessage):  # type: ignore[reportIncompatibleMethodOverride]
        # 1. 记录接收到的事件
        delay_ms = int(time.time() * 1000) - (event.headers.event_born_time or 0)
        logger.info(
            "收到事件: delay=%sms, eventType=%s, eventId=%s",
            delay_ms,
            event.headers.event_type,
            event.headers.event_id,
        )
        headers = event.headers.to_dict()
        headers.update(
            {
                "eventType": event.headers.event_type,
                "eventId": event.headers.event_id,
                "eventBornTime": event.headers.event_born_time,
                "eventCorpId": event.headers.event_corp_id,
                "eventUnifiedAppId": event.headers.event_unified_app_id,
            }
        )
        # 2. 处理事件数据
        event_data = {
            # SDK EventMessage.from_dict 只识别 specVersion，必须同时写入；
            # 保留 spec_version 以兼容存量消息消费者
            "specVersion": event.spec_version,
            "spec_version": event.spec_version,
            "type": event.type,
            "headers": headers,
            "data": json.dumps(event.data),
            "extensions": event.extensions,
        }
        connection = None
        try:
            connection = pika.BlockingConnection(pika.URLParameters(url=settings.RABBITMQ_CONFIG["url"]))
            channel = connection.channel()
            channel.exchange_declare(
                exchange=settings.RABBITMQ_CONFIG["exchange_name"],
                exchange_type=settings.RABBITMQ_CONFIG["exchange_type"],
                durable=settings.RABBITMQ_CONFIG["durable"],
            )
            channel.basic_publish(
                exchange=settings.RABBITMQ_CONFIG["exchange_name"],
                routing_key="",
                body=json.dumps(event_data).encode("utf-8"),
            )
        finally:
            if connection is not None and getattr(connection, "is_open", False):
                connection.close()
        return dingtalk_stream.AckMessage.STATUS_OK, "OK"


class Subscriber(object):
    def __init__(self, func, max_retries=-1, retry_interval=5):
        """
        钉钉 Stream 消息订阅者
        
        Args:
            func: 消息处理函数
            max_retries: 最大重试次数，-1 表示无限重试
            retry_interval: 重试间隔（秒）
        """
        self.func = func
        self.max_retries = max_retries
        self.retry_interval = retry_interval
        self.should_stop = False

    def execute(self):
        """执行消息消费，带自动重连机制"""
        retry_count = 0
        
        while not self.should_stop:
            try:
                self._consume_messages()
            except AMQPConnectionError as e:
                logger.error(f"RabbitMQ 连接断开: {str(e)}")
                retry_count += 1
                
                # 检查是否超过最大重试次数
                if self.max_retries != -1 and retry_count >= self.max_retries:
                    logger.error(f"达到最大重试次数 {self.max_retries}，退出程序")
                    break
                
                logger.info(f"{self.retry_interval} 秒后开始第 {retry_count + 1} 次重试...")
                time.sleep(self.retry_interval)
                
            except Exception as e:
                logger.error(f"发生未知错误: {str(e)}")
                retry_count += 1
                
                if self.max_retries != -1 and retry_count >= self.max_retries:
                    logger.error(f"达到最大重试次数 {self.max_retries}，退出程序")
                    break
                
                time.sleep(self.retry_interval)

    def _consume_messages(self):
        """消费消息的核心逻辑"""
        # 1. 配置RabbitMQ连接
        exchange_name = settings.RABBITMQ_CONFIG["exchange_name"]
        queue_name = settings.RABBITMQ_CONFIG["queue_name"]

        # 2. 建立连接（添加心跳和超时配置）
        parameters = pika.URLParameters(settings.RABBITMQ_CONFIG["url"])
        parameters.heartbeat = 60  # 心跳间隔 60 秒
        parameters.connection_attempts = 3  # 连接尝试次数
        parameters.retry_delay = 5  # 重试延迟
        
        connection = pika.BlockingConnection(parameters)
        channel = connection.channel()

        # 3. 声明交换机
        channel.exchange_declare(
            exchange=exchange_name,
            exchange_type=settings.RABBITMQ_CONFIG["exchange_type"],
            durable=settings.RABBITMQ_CONFIG["durable"],
        )

        # 4. 声明队列
        channel.queue_declare(queue=queue_name, durable=True)

        # 5. 绑定队列到交换机
        channel.queue_bind(exchange=exchange_name, queue=queue_name)

        # 6. 设置 QoS（预取数量），避免处理不过来
        channel.basic_qos(prefetch_count=1)

        def callback(ch, method, properties, body):  # pyright: ignore[reportUnusedVariable]
            try:
                # 解析消息
                message = json.loads(body.decode("utf-8"))
                headers = message.get("headers") or {}
                logger.info(
                    "收到消息: eventType=%s eventId=%s",
                    headers.get("eventType"),
                    headers.get("eventId"),
                )
                event = EventMessage.from_dict(message)
                self.func.execute(event)
                # 手动确认消息
                ch.basic_ack(delivery_tag=method.delivery_tag)
            except Exception as e:
                logger.error(f"处理消息错误: {str(e)}")
                # 消息处理失败，拒绝消息但不重新入队
                ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)

        # 7. 开始消费消息
        args = {"x-priority": settings.RABBITMQ_CONFIG.get("x-priority", 0)}
        channel.basic_consume(queue=queue_name, on_message_callback=callback, auto_ack=False, arguments=args)

        logger.info(f"[*] 等待接收消息, 队列名: {queue_name}")
        
        # 开始消费（会阻塞直到连接断开）
        channel.start_consuming()
