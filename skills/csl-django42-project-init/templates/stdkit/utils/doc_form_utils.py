import jinja2
from docxtpl import DocxTemplate, InlineImage
from docx.shared import Mm


def get_all_nodes(docx_file_path):
    """获取文件中的表达式名字(类似从 {{ tag_name }} 中获取tag_name)"""
    docx = DocxTemplate(docx_file_path)
    docx.init_docx()
    xml_string = docx.patch_xml(docx.get_xml())
    jenv = jinja2.Environment()
    docx_ast = jenv.parse(xml_string)

    tag_name_list = []

    for i in docx_ast.body[0].nodes:
        if "name" in i.fields:
            tag_name_list.append(i.name)

    return tag_name_list


def render_file(output_file_path, form_docx_file_path, tag_values=None):
    """
    渲染模板文件到输出
    :param output_file_path:
    :param form_docx_file_path:
    :param tag_values: list[{'tag_type':'', 'tag':'', 'value':''}]
    :return:
    """

    tpl = DocxTemplate(form_docx_file_path)
    context_dict = {}
    for tag_value in (tag_values or []):
        if tag_value["tag_type"] == "image":
            context_dict[tag_value["tag"]] = InlineImage(tpl, tag_value["value"], height=Mm(300))
        else:
            context_dict[tag_value["tag"]] = tag_value["value"]
    jinja_env = jinja2.Environment(autoescape=True)
    tpl.render(context_dict, jinja_env)
    tpl.save(str(output_file_path))
