# Stop sign violation detection and license plate recognition

Based on YOLOV7 object detection library engine from WongKinYiu repository on   https://github.com/WongKinYiu/yolov7
and DeepSort object tracking implementation  
https://github.com/RizwanMunawar/yolov7-object-tracking/  

First:
``` shell
pip install -r requirements.txt  
```

Then:
Download pretrained yolov7-tiny or yolov7 weights from YOLOV7 assets repository  
https://github.com/WongKinYiu/yolov7/releases

Download stop_sign.mp4  https://drive.google.com/file/d/11gLLNV617L8wIl3-YV3Tcdr3IUUfrk7J/view?usp=sharing


Run with yolo7 tiny model weights(Recommended):
``` shell
python detect_stop_sign.py --source ./stop_sign.mp4 --weights yolov7-tiny.pt --name "stop sign" --view-img --classes 2 --cropping 0 700 0 700 --sensitivity 50 --cam-fps 25

```

Run with yolo7 normal model weights:
``` shell
python detect_stop_sign.py --source ./stop_sign.mp4 --weights yolov7.pt --name "stop sign" --view-img --classes 2 --cropping 0 700 0 700 --sensitivity 50 --cam-fps 25

```

classes 2 = car class

---
#### Backend: 

Each car that is detected within the area of interest can stored to the database by setting the --upload flag:
``` shell
python detect_stop_sign.py 
--source ./stop_sign.mp4 
--weights yolov7.pt --name "stop sign" 
--view-img --classes 2 --cropping 0 700 0 700 
--sensitivity 50 --cam-fps 25 
--upload
```



Right now, the direction, date, speed, category and convoytype are stored into the database.

Standard URL: localhost:3000




