# Debian slim => python:3.11.2-slim (Debugging only)
# Alpine => python:3.11.2-alpine
# eliona => eliona/base-python:latest-3.11-alpine
# eliona => eliona/base-python:latest-3.11-alpine-eliona
FROM eliona/base-python:latest-3.11-alpine-eliona

# Set the workingdirectory for the application
WORKDIR /app

# Add applications packages
RUN apk add --update --no-cache git build-base 

#Add the needded data and install the python app requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Add files and directorys
COPY ./storage ./storage
COPY ./testing ./testing
COPY ./src .

#Start the python application
CMD ["python", "spreadsheet-report-app/spreadsheet_report_app.py", "-m runtime"]