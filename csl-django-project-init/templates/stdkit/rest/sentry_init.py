import logging
try:
    from raven import Client
    from raven.transport.http import HTTPTransport
except ImportError:
    Client = None
    HTTPTransport = None

_client = None
logger = logging.getLogger("django")

def get_client(dsn=None, environment=None):
    global _client
    if _client:
        return _client
    
    if Client and dsn:
        try:
            # Initialize Raven Client with synchronous transport
            _client = Client(dsn=dsn, environment=environment, transport=HTTPTransport)
            return _client
        except Exception as e:
            logger.error(f"Failed to initialize Raven client: {e}")
            return None
    return None

def init_sentry(config=None):
    """
    Initialize Sentry with a config dictionary (e.g. from settings_local.RAVEN_CONFIG).
    args:
        config: dict containing 'dsn' and optional 'environment'
    """
    if config is None:
        config = {}
    
    dsn = config.get("dsn")
    environment = config.get("environment", "online")
    
    if dsn:
        get_client(dsn, environment)

def capture_exception(exc):
    """
    Capture raw exception using Raven.
    """
    client = get_client()
    if client:
        if exc is None:
            # 兼容旧行为：无异常对象时上报当前活动异常
            client.captureException(exc_info=True)
        else:
            client.captureException(exc_info=(type(exc), exc, getattr(exc, "__traceback__", None)))

def capture_message(message):
    """
    Capture message using Raven.
    """
    client = get_client()
    if client:
        client.captureMessage(message)
