FROM python:3.11.3-slim

# Set the workingdirectory for the application
WORKDIR /app

######## Debian add apendancies ###########
RUN apt update
RUN apt install -y git

#Add the needded data
COPY requirements.txt .

#install the python app requirements
RUN pip install --no-cache-dir -r requirements.txt

COPY ./src .
COPY ./storage ./storage
COPY ./testing ./testing


#Start the python application
CMD ["python", "spreadsheet-report-app/spreadsheet_report_app.py", "-m runtime"]