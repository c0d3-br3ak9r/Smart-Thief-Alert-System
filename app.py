import os
import time
from flask import Flask, Response, render_template, request
import random
import cv2
from notify_run import Notify
import numpy as np
import smtplib
import imghdr
from email.message import EmailMessage


app = Flask(__name__)

notify = Notify()

y_path = r'yolo-coco'

sent_mail = False

gui_confidence = .6     # initial settings
gui_threshold = .3      # initial settings
camera_number = 0       # if you have more than 1 camera, change this variable to choose which is used

# load the COCO class labels our YOLO model was trained on
labelsPath = os.path.sep.join([y_path, "coco.names"])
LABELS = open(labelsPath).read().strip().split("\n")

# initialize a list of colors to represent each possible class label
np.random.seed(42)
COLORS = np.random.randint(0, 255, size=(len(LABELS), 3), dtype="uint8")

# derive the paths to the YOLO weights and model configuration
weightsPath = os.path.sep.join([y_path, "yolov3.weights"])
configPath = os.path.sep.join([y_path, "yolov3.cfg"])

net = cv2.dnn.readNetFromDarknet(configPath, weightsPath)
ln = net.getLayerNames()
# ln = [ln[i[0] - 1] for i in net.getUnconnectedOutLayers()]        # old code changed on Feb-4-2022
ln = [ln[i - 1] for i in net.getUnconnectedOutLayers()]

# initialize the video stream, pointer to output video file, and
# frame dimensions
W, H = None, None
win_started = False


camera = cv2.VideoCapture(0)  

def is_human_detected():
    W, H = None, None
    grabbed, frame = camera.read()

    # if the frame was not grabbed, then we stream has stopped so break out
    if not grabbed:
        return

    # if the frame dimensions are empty, grab them
    if not W or not H:
        (H, W) = frame.shape[:2]

    # construct a blob from the input frame and then perform a forward
    # pass of the YOLO object detector, giving us our bounding boxes
    # and associated probabilities
    blob = cv2.dnn.blobFromImage(frame, 1 / 255.0, (416, 416),
                                 swapRB=True, crop=False)
    net.setInput(blob)
    start = time.time()
    layerOutputs = net.forward(ln)
    end = time.time()

    # initialize our lists of detected bounding boxes, confidences,
    # and class IDs, respectively
    boxes = []
    confidences = []
    classIDs = []

    # loop over each of the layer outputs
    for output in layerOutputs:
        # loop over each of the detections
        for detection in output:
            # extract the class ID and confidence (i.e., probability)
            # of the current object detection
            scores = detection[5:]
            classID = np.argmax(scores)
            confidence = scores[classID]

            #print("+++" + scores + "+++" + classID + "+++" + confidence)

            # filter out weak predictions by ensuring the detected
            # probability is greater than the minimum probability
            if confidence > gui_confidence:
                # scale the bounding box coordinates back relative to
                # the size of the image, keeping in mind that YOLO
                # actually returns the center (x, y)-coordinates of
                # the bounding box followed by the boxes' width and
                # height
                box = detection[0:4] * np.array([W, H, W, H])
                (centerX, centerY, width, height) = box.astype("int")

                # use the center (x, y)-coordinates to derive the top
                # and and left corner of the bounding box
                x = int(centerX - (width / 2))
                y = int(centerY - (height / 2))

                # update our list of bounding box coordinates,
                # confidences, and class IDs
                boxes.append([x, y, int(width), int(height)])
                confidences.append(float(confidence))
                classIDs.append(classID)

    # apply non-maxima suppression to suppress weak, overlapping bounding boxes
    idxs = cv2.dnn.NMSBoxes(boxes, confidences, gui_confidence, gui_threshold)

    # ensure at least one detection exists
    if len(idxs) > 0:
        # loop over the indexes we are keeping
        for i in idxs.flatten():
            # extract the bounding box coordinates
            (x, y) = (boxes[i][0], boxes[i][1])
            (w, h) = (boxes[i][2], boxes[i][3])
            # draw a bounding box rectangle and label on the frame
            color = [int(c) for c in COLORS[classIDs[i]]]
            cv2.rectangle(frame, (x, y), (x + w, y + h), color, 2)
            text = "{}: {:.4f}".format(LABELS[classIDs[i]],
                                       confidences[i])

            cv2.imwrite('alert.jpg',frame)
            return LABELS[classIDs[i]] == "person"

def gen_frames():  
    while True:
        success, frame = camera.read() 
        if not success:
            break
        else:
            ret, buffer = cv2.imencode('.jpg', frame)
            frame = buffer.tobytes()
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n') 


def send_email():
    Sender_Email = "example@example.com"
    Reciever_Email = "example@example.com"
    Password = "ExamplePassword"
    newMessage = EmailMessage()                         
    newMessage['Subject'] = "INTRUDER ALERT!!!" 
    newMessage['From'] = Sender_Email                   
    newMessage['To'] = Reciever_Email                   
    newMessage.set_content('Let me know what you think. Image attached!. Visit this URL foor live feed http://192.168.139.214:5000/video') 
    with open('alert.jpg', 'rb') as f:
        image_data = f.read()
        image_type = imghdr.what(f.name)
        image_name = f.name
    newMessage.add_attachment(image_data, maintype='image', subtype=image_type, filename=image_name)
    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
        
        smtp.login(Sender_Email, Password)              
        smtp.send_message(newMessage)


@app.route('/video_feed')
def video_feed():
    return Response(gen_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')


@app.route('/video')
def video():
    """Video streaming home page."""
    return render_template('index.html')

def notify_user(msg):
    notify.send(msg, 'http://192.168.139.214:5000/video')


@app.route('/', methods=["POST"])
def index():
    global sent_mail
    if ( request.json["soundDetected"] ):
        notify_user("Sound Detected!!!")
        print("Sound Detected")
    if ( request.json["motionDetected"] ):
        print("Motion Detected")
        notify_user("Motion Detected!!!")
        if ( is_human_detected() ):
            #if ( not sent_mail ):
                notify_user("HIGH ALERT! INTRUDER DETECTED!!!")
                send_email()
                #sent_mail = True
    if ( request.json["distanceDetected"] ):
        print("Distance Detected")
        notify_user("Someone is nearing!!!")
        if ( is_human_detected() ):
            #if ( not sent_mail ):
                notify_user("HIGH ALERT! INTRUDER DETECTED!!!")
                send_email()
                #sent_mail = True

    return "Hello, World! " + str(random.randint(0, 100)) + " " + str(request.data)

app.run(host="192.168.139.214", port=5000, debug=True)