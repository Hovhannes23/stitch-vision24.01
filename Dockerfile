FROM python:3.8
RUN apt-get update -y && apt-get install -y python3-pip python3 python-dev &&  python3 -m pip install --upgrade pip
WORKDIR /app
COPY . /app
RUN pip3 install pillow-heif
RUN pip3 install -r pythonProject3/requirements.txt
RUN apt-get install ffmpeg libsm6 libxext6  -y
COPY . /app
EXPOSE 5000
#CMD ["python", "pythonProject3/controller/main_controller.py"]
CMD [ "flask", "--app" , "pythonProject3.controller.main_controller.py", "run"]

