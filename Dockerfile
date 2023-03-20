FROM python:3.11.2-alpine3.17

#Add the needded data
ADD ./src .
ADD requirements.txt .
ADD ./tmp_reports .

#install the requirements
RUN pip install --no-cache-dir -r requirements.txt

#Start the python application
CMD [ "python", "./src/spreadsheet_report_app.py"]
