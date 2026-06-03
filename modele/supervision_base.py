# coding: utf-8
from MySQLdb.cursors import DictCursor

class _Base:
    def __init__(self, mysql):
        self.mysql = mysql

    def _cursor(self):
        return self.mysql.connection.cursor(DictCursor)

    def _commit(self):
        self.mysql.connection.commit()
