def get_real_max_row(sheet):
    """
    获取工作表中有数据的最大行数（避免返回因格式等原因造成的最大行）。
    从 max_row 开始向上查找，直到找到第一行非空单元格。
    """
    # 初始化真实的最大行号为0
    real_max_row = 0
    # 从 sheet.max_row 开始向上遍历（避免从绝对最大行数1048576开始，提高效率）
    for row in range(sheet.max_row, 0, -1):
        # 检查该行的每一个单元格是否并非全部为 None 或空字符串
        # 使用列表推导式检查一行中所有单元格的值
        if any(cell.value is not None and str(cell.value).strip() != '' for cell in sheet[row]):
            real_max_row = row
            break # 找到第一个有数据的行就跳出循环
    # 如果一行数据都没找到，则返回0或1（取决于你的需求，例如没有数据时是否包含标题行）
    # 这里简单返回 real_max_row，有可能为0
    return real_max_row