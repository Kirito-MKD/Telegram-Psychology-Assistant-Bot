import os
import pandas as pd
import openpyxl
from tools import get_time

class Exel():
    def __init__(self):
        self.columns = ["Дата последенего взаимодействия", "Имя", "Никнейм", "Телефон"]
        self.file_name = "statistic.xlsx"
        self.ws = ""

        self.workbook = openpyxl.Workbook()
        self.ws = self.workbook.active
        self.ws.append(self.columns)
        self.ws.insert_rows(1)

    def _format(self):
        for col in self.ws.columns:
            max_length = 0
            column = col[0].column_letter  # Get the column name
            for cell in col:
                try:  # Necessary to avoid error on empty cells
                    if len(str(cell.value)) > max_length:
                        max_length = len(str(cell.value))
                except:
                    pass
            adjusted_width = (max_length + 2) * 1.2
            self.ws.column_dimensions[column].width = adjusted_width

    def build(self, users):
        for user in users:
            to_write = [user[0], user[1], user[2], user[3]]
            self.ws.append(to_write)

        self.ws.insert_rows(len(to_write))
        self._format()
        self.workbook.save(self.file_name)
        return self.file_name