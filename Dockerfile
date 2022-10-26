FROM python:3.10.6-bullseye

#Add the needded data
ADD KarlaKolumna.py .
ADD requirements.txt .
ADD ./templates .

#install the requirements
RUN pip install --no-cache-dir -r requirements.txt

#Start the python application
CMD [ "python", "./KarlaKolumna.py"]
