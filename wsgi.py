# coding: utf-8
import os

os.environ.setdefault('OMP_NUM_THREADS', '1')

from application import Application


app = Application().app
