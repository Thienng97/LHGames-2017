FROM polyhx/python-seed

ADD . .

EXPOSE 8080

CMD ["python", "ai.py"]
