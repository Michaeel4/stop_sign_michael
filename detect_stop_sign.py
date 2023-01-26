#!/usr/bin/env python3
import argparse
import time
from pathlib import Path
import cv2
import torch
import torch.backends.cudnn as cudnn
from numpy import random

from models.experimental import attempt_load
from utils.datasets import LoadStreams, LoadImages, set_cropping, set_cropping_values
from utils.general import check_img_size, check_requirements, \
    check_imshow, non_max_suppression, apply_classifier, \
    scale_coords, xyxy2xywh, strip_optimizer, set_logging, \
    increment_path
from utils.plots import plot_one_box
from utils.torch_utils import select_device, load_classifier, time_synchronized, TracedModel

# For SORT tracking
import skimage
from sort import *

import time

from upload import upload_info

from vehicle import Vehicle

# ............................... Tracker Functions ............................
""" Random created palette"""
palette = (2 ** 11 - 1, 2 ** 15 - 1, 2 ** 20 - 1)

# lines for car counting
area1_pointA = (104, 199)
area1_pointB = (305, 237)
area1_pointC = (19, 345)
area1_pointD = (286, 320)

# stopsign stopping area
stop_area = [(62, 162), (20, 333), (283, 311), (305, 237)]

# areas for speed calculation
start_speed_area = [(200, 154), (180, 164), (305, 237), (322, 228)]
stop_speed_area = [(19, 344), (9, 371), (294, 348), (286, 320)]

# vehicles total counting variables
array_ids = []
counting = 0
modulo_counting = 0

# tracking vehicles
vehicles_entering = {}
vehicles_elapsed_time = {}
distance = 9
camera_fps = 25
sensitivity_stop = 1
speed = 0  # speed of last measured vehicle
stopped = False  # stopp indicator boolean
curr_id = 0
l_midpoint_x = 0  # previous frame midpoints
l_midpoint_y = 0
l_cp_distance_x = 0  # midpoint distances
l_cp_distance_y = 0
counter = 0  # counter to measure midpoints distance every x frames
upload_data = False
label = ""
"""" Calculates the relative bounding box from absolute pixel values. """


def bbox_rel(*xyxy):
    bbox_left = min([xyxy[0].item(), xyxy[2].item()])
    bbox_top = min([xyxy[1].item(), xyxy[3].item()])
    bbox_w = abs(xyxy[0].item() - xyxy[2].item())
    bbox_h = abs(xyxy[1].item() - xyxy[3].item())
    x_c = (bbox_left + bbox_w / 2)
    y_c = (bbox_top + bbox_h / 2)
    w = bbox_w
    h = bbox_h
    return x_c, y_c, w, h


"""Simple function that adds fixed color depending on the class"""


def compute_color_for_labels(label):
    color = [int((p * (label ** 2 - label + 1)) % 255) for p in palette]
    return tuple(color)


"""Function to Draw Bounding boxes"""


def draw_boxes(img, bbox, identities=None, categories=None, names=None, offset=(0, 0)):


    global camera_fps
    global sensitivity_stop
    global l_midpoint_x
    global l_midpoint_y
    global l_cp_distance_x
    global l_cp_distance_y
    global counter
    global stopped
    global curr_id
    global label

    for i, box in enumerate(bbox):
        x1, y1, x2, y2 = [int(i) for i in box]
        x1 += offset[0]
        x2 += offset[0]
        y1 += offset[1]
        y2 += offset[1]
        cat = int(categories[i]) if categories is not None else 0
        id = int(identities[i]) if identities is not None else 0
        color = compute_color_for_labels(id)
        data = (int((box[0] + box[2]) / 2), (int((box[1] + box[3]) / 2)))
        label = str(id) + ":" + names[cat]
        (w, h), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 1)

        cv2.circle(img, data, 6, color, -1)
        midpoint_x = x1 + ((x2 - x1) / 2)
        midpoint_y = y1 + ((y2 - y1) / 2)
        center_point = (int(midpoint_x), int(midpoint_y))

        midpoint_color = (0, 0, 255)

        # check if object is in the start_area box
        in_start_speed_area = cv2.pointPolygonTest(np.array(start_speed_area, np.int32), (int(x1), int(y2)),
                                                   False)  # point for speed measuring is the lower left point of the detection rectangle
        # check if object is in the stop_sign_area
        in_stop_sign_area = cv2.pointPolygonTest(np.array(stop_area, np.int32), (int(midpoint_x), int(midpoint_y)),
                                                 False)

        if in_stop_sign_area >= 0:
            if curr_id != id:  # new id stopped to false
                stopped = False
            counter = counter + 1
            if counter % round(
                    camera_fps * sensitivity_stop / 100) == 0 or counter == 0:  # check the midpoint distance every 25 frames
                l_cp_distance_x = abs(l_midpoint_x - midpoint_x)
                l_cp_distance_y = abs(l_midpoint_y - midpoint_y)
                print("x_distance: " + str(l_cp_distance_x) + " y_distance: " + str(l_cp_distance_y))
                if l_cp_distance_x < 0.1 and l_cp_distance_y < 0.1:
                    stopped = True
                    curr_id = id
                    print("Vehicle has stopped")



            l_midpoint_x = midpoint_x
            l_midpoint_y = midpoint_y

        if in_start_speed_area >= 0:
            vehicles_entering[id] = time.time()

        if id in vehicles_entering:
            # print("in start area")
            in_stop_speed_area = cv2.pointPolygonTest(np.array(stop_speed_area, np.int32), (int(x1), int(y2)),
                                                      False)  # point for speed measuring is the lower left point of the detection rectangle

            if in_stop_speed_area >= 0:
                # print("in stop area")
                elapsed_time = time.time() - vehicles_entering[id]

                if id not in vehicles_elapsed_time:
                    vehicles_elapsed_time[id] = elapsed_time

                if id in vehicles_elapsed_time:
                    elapsed_time = vehicles_elapsed_time[id]

                a_speed_ms = distance / elapsed_time
                a_speed_kh = a_speed_ms * 3.6  # calculate speed
                global speed
                speed = a_speed_kh
                # print(elapsed_time)
                # cv2.rectangle(img, (x1, y1), (x2, y2), (0,0,255), 1)
                # cv2.rectangle(img, (x1, y1 - 20), (x1 + w + 100, y1), (255,144,30), -1)
                # cv2.putText(img, "Speed "+str(int(a_speed_kh))+" km/h", (x1, y1 - 5),cv2.FONT_HERSHEY_SIMPLEX, 0.6, [255, 255, 255], 1)

                # cv2.circle(img, data, 6, color,-1)
            '''
            else:
                cv2.rectangle(img, (x1, y1), (x2, y2), (255,144,30), 1)
                #cv2.rectangle(img, (x1, y1 - 20), (x1 + w, y1), (255,144,30), -1)
                cv2.putText(img, label, (x1, y1 - 5),cv2.FONT_HERSHEY_SIMPLEX, 0.6, [255, 255, 255], 1)
                # cv2.circle(img, data, 6, color,-1)
            '''

            # if (midpoint_x > area1_pointA[0] and midpoint_x < area1_pointD[0]) and (midpoint_y > area1_pointA[1] and midpoint_y < area1_pointD[1]):
            #     cv2.rectangle(img, (x1, y1), (x2, y2), (255,144,30), 1)
            #     cv2.rectangle(img, (x1, y1 - 20), (x1 + w, y1), (255,144,30), -1)
            #     cv2.putText(img, label, (x1, y1 - 5),cv2.FONT_HERSHEY_SIMPLEX, 0.6, [255, 255, 255], 1)
            #     midpoint_color = (0,0,255)

            # add vehicles counting
            if len(array_ids) > 0:
                if id not in array_ids:
                    array_ids.append(id)

                    print(speed)
                    print(stopped)

                    if (upload_data ==True):
                        vehicle = Vehicle(id, time, "forward", cat, 0, speed, 0, 0, 0, identities)
                        upload_info(vehicle)





            else:
                array_ids.append(id)

                if(upload_data == True):
                    vehicle = Vehicle(id, time, "forward", cat, 0, speed, 0, 0, 0, identities)
                    upload_info(vehicle)




                #vehicle = Vehicle(id, time, "forward", cat, 0, speed, 0, 0, 0, identities)
                #upload_info(vehicle)

        cv2.rectangle(img, (x1, y1), (x2, y2), (255, 144, 30), 1)
        cv2.rectangle(img, (x1, y1 - 20), (x1 + w, y1), (255, 144, 30), -1)
        cv2.putText(img, label, (x1, y1 - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.6, [255, 255, 255], 1)
        midpoint_color = (0, 0, 255)

        cv2.circle(img, center_point, radius=1, color=midpoint_color, thickness=5)

    return img


# ..............................................................................


def detect(save_img=False):

    global upload_data


    upload_data = opt.upload
    source, weights, view_img, save_txt, imgsz, trace, cropping, cam_fps, sensitivity = opt.source, opt.weights, opt.view_img, opt.save_txt, opt.img_size, not opt.no_trace, opt.cropping, opt.cam_fps, opt.sensitivity
    save_img = not opt.nosave and not source.endswith('.txt')  # save inference images
    webcam = source.isnumeric() or source.endswith('.txt') or source.lower().startswith(
        ('rtsp://', 'rtmp://', 'http://', 'https://'))
    global camera_fps
    global sensitivity_stop
    camera_fps = cam_fps
    sensitivity_stop = sensitivity
    if cropping:
        set_cropping_values(cropping)
        set_cropping(True)

    # .... Initialize SORT ....
    # .........................
    sort_max_age = 5
    sort_min_hits = 2
    sort_iou_thresh = 0.2
    sort_tracker = Sort(max_age=sort_max_age,
                        min_hits=sort_min_hits,
                        iou_threshold=sort_iou_thresh)
    # .........................
    # Directories
    save_dir = Path(increment_path(Path(opt.project) / opt.name, exist_ok=opt.exist_ok))  # increment run
    (save_dir / 'labels' if save_txt else save_dir).mkdir(parents=True, exist_ok=True)  # make dir

    # Initialize
    set_logging()
    device = select_device(opt.device)
    half = device.type != 'cpu'  # half precision only supported on CUDA
    half = False

    # Load model
    model = attempt_load(weights, map_location=device)  # load FP32 model
    stride = int(model.stride.max())  # model stride
    imgsz = check_img_size(imgsz, s=stride)  # check img_size

    if trace:
        model = TracedModel(model, device, opt.img_size)

    if half:
        model.half()  # to FP16

    # Second-stage classifier
    classify = False
    if classify:
        modelc = load_classifier(name='resnet101', n=2)  # initialize
        modelc.load_state_dict(torch.load('weights/resnet101.pt', map_location=device)['model']).to(device).eval()

    # Set Dataloader
    vid_path, vid_writer = None, None
    if webcam:
        view_img = check_imshow()
        cudnn.benchmark = True  # set True to speed up constant image size inference
        dataset = LoadStreams(source, img_size=imgsz, stride=stride)
    else:
        dataset = LoadImages(source, img_size=imgsz, stride=stride)

    # Get names and colors
    names = model.module.names if hasattr(model, 'module') else model.names
    colors = [[random.randint(0, 255) for _ in range(3)] for _ in names]

    # Run inference
    if device.type != 'cpu':
        model(torch.zeros(1, 3, imgsz, imgsz).to(device).type_as(next(model.parameters())))  # run once
    old_img_w = old_img_h = imgsz
    old_img_b = 1

    count_vehicle = 0

    t0 = time.time()
    for path, img, im0s, vid_cap in dataset:
        img = torch.from_numpy(img).to(device)
        img = img.half() if half else img.float()  # uint8 to fp16/32
        img /= 255.0  # 0 - 255 to 0.0 - 1.0
        if img.ndimension() == 3:
            img = img.unsqueeze(0)

        # Warmup
        if device.type != 'cpu' and (
                old_img_b != img.shape[0] or old_img_h != img.shape[2] or old_img_w != img.shape[3]):
            old_img_b = img.shape[0]
            old_img_h = img.shape[2]
            old_img_w = img.shape[3]
            for i in range(3):
                model(img, augment=opt.augment)[0]

        # Inference
        t1 = time_synchronized()
        pred = model(img, augment=opt.augment)[0]
        t2 = time_synchronized()

        # Apply NMS
        pred = non_max_suppression(pred, opt.conf_thres, opt.iou_thres, classes=opt.classes, agnostic=opt.agnostic_nms)
        t3 = time_synchronized()

        # Apply Classifier
        if classify:
            pred = apply_classifier(pred, modelc, img, im0s)

        # Process detections
        for i, det in enumerate(pred):  # detections per image
            if webcam:  # batch_size >= 1
                p, s, im0, frame = path[i], '%g: ' % i, im0s[i].copy(), dataset.count
            else:
                p, s, im0, frame = path, '', im0s, getattr(dataset, 'frame', 0)

            p = Path(p)  # to Path

            save_path = str(save_dir / p.name)  # img.jpg
            txt_path = str(save_dir / 'labels' / p.stem) + (
                '' if dataset.mode == 'image' else '{frame}'.format(frame=frame))  # img.txt
            gn = torch.tensor(im0.shape)[[1, 0, 1, 0]]  # normalization gain whwh
            if len(det):
                # Rescale boxes from img_size to im0 size
                det[:, :4] = scale_coords(img.shape[2:], det[:, :4], im0.shape).round()

                # Print results
                for c in det[:, -1].unique():
                    n = (det[:, -1] == c).sum()  # detections per class
                    s += f"{n} {names[int(c)]}{'s' * (n > 1)}, "  # add to string

                # ..................USE TRACK FUNCTION....................
                # pass an empty array to sort
                dets_to_sort = np.empty((0, 6))

                # NOTE: We send in detected object class too
                for x1, y1, x2, y2, conf, detclass in det.cpu().detach().numpy():
                    dets_to_sort = np.vstack((dets_to_sort,
                                              np.array([x1, y1, x2, y2, conf, detclass])))

                # Run SORT
                tracked_dets = sort_tracker.update(dets_to_sort)
                tracks = sort_tracker.getTrackers()

                # print('Tracked Detections : '+str(len(tracked_dets)))

                # loop over tracks
                '''
                for track in tracks:
                    # color = compute_color_for_labels(id)
                    #draw tracks

                    [cv2.line(im0, (int(track.centroidarr[i][0]),
                                    int(track.centroidarr[i][1])), 
                                    (int(track.centroidarr[i+1][0]),
                                    int(track.centroidarr[i+1][1])),
                                    (0,255,0), thickness=1) 
                                    for i,_ in  enumerate(track.centroidarr) 
                                        if i < len(track.centroidarr)-1 ] 
                '''

                # draw boxes for visualization
                if len(tracked_dets) > 0:
                    bbox_xyxy = tracked_dets[:, :4]
                    identities = tracked_dets[:, 8]
                    categories = tracked_dets[:, 4]
                    draw_boxes(im0, bbox_xyxy, identities, categories, names)





                # ........................................................

            # Print time (inference + NMS)
            # print(f'{s}Done. ({(1E3 * (t2 - t1)):.1f}ms) Inference, ({(1E3 * (t3 - t2)):.1f}ms) NMS')

            cv2.line(im0, area1_pointA, area1_pointB, (0, 255, 0), 2)
            cv2.line(im0, area1_pointC, area1_pointD, (0, 255, 0), 2)

            color = (0, 255, 0)
            thickness = 2
            fontScale = 1
            font = cv2.FONT_HERSHEY_SIMPLEX
            org = (25, 29)

            if (count_vehicle == 0):
                counting = len(array_ids)
            else:
                if (counting < 100):
                    counting = len(array_ids)
                else:
                    counting = modulo_counting + len(array_ids)
                    if (len(array_ids) % 100 == 0):
                        modulo_counting = modulo_counting + 100
                        array_ids.clear()

            cv2.putText(im0, 'Vehicle Counting = ' + str(counting), org, font, fontScale, color, thickness, cv2.LINE_AA)

            cv2.putText(im0, 'Avg-Speed = ' + str(int(speed)) + ' km/h', (org[0], org[1] + 50), font, fontScale, color,
                        thickness, cv2.LINE_AA)

            cv2.putText(im0, 'Stopped? = ' + str(stopped), (org[0], org[1] + 100), font, fontScale, color, thickness,
                        cv2.LINE_AA)






            #upload_info(vehicle)
            # draw stop_area
            cv2.polylines(im0, [np.array(stop_area, np.int32)], True, (255, 0, 0), 2)

            # draw _speed_start_area
            cv2.polylines(im0, [np.array(start_speed_area, np.int32)], True, color, 2)

            # draw speed_stop_area
            cv2.polylines(im0, [np.array(stop_speed_area, np.int32)], True, color, 2)

            # Stream results
            if view_img:
                cv2.imshow(str(p), im0)
                cv2.waitKey(1)  # 1 millisecond

            # Save results (image with detections)
            if save_img:
                if dataset.mode == 'image':
                    cv2.imwrite(save_path, im0)
                    print(f" The image with the result is saved in: {save_path}")
                else:  # 'video' or 'stream'
                    if vid_path != save_path:  # new video
                        vid_path = save_path
                        if isinstance(vid_writer, cv2.VideoWriter):
                            vid_writer.release()  # release previous video writer
                        if vid_cap:  # video
                            fps = vid_cap.get(cv2.CAP_PROP_FPS)
                            w = int(vid_cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                            h = int(vid_cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                        else:  # stream
                            fps, w, h = 30, im0.shape[1], im0.shape[0]
                            save_path += '.mp4'
                        vid_writer = cv2.VideoWriter(save_path, cv2.VideoWriter_fourcc(*'mp4v'), fps, (w, h))
                    vid_writer.write(im0)

    if save_txt or save_img:
        s = f"\n{len(list(save_dir.glob('labels/*.txt')))} labels saved to {save_dir / 'labels'}" if save_txt else ''
        # print(f"Results saved to {save_dir}{s}")

    print(f'Done. ({time.time() - t0:.3f}s)')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--weights', nargs='+', type=str, default='yolov7.pt', help='model.pt path(s)')
    parser.add_argument('--source', type=str, default='inference/images', help='source')  # file/folder, 0 for webcam
    parser.add_argument('--img-size', type=int, default=640, help='inference size (pixels)')
    parser.add_argument('--conf-thres', type=float, default=0.65, help='object confidence threshold')
    parser.add_argument('--iou-thres', type=float, default=0.45, help='IOU threshold for NMS')
    parser.add_argument('--device', default='', help='cuda device, i.e. 0 or 0,1,2,3 or cpu')
    parser.add_argument('--view-img', action='store_true', help='display results')
    parser.add_argument('--save-txt', action='store_true', help='save results to *.txt')
    parser.add_argument('--save-conf', action='store_true', help='save confidences in --save-txt labels')
    parser.add_argument('--nosave', action='store_true', help='do not save images/videos')
    parser.add_argument('--classes', nargs='+', type=int, help='filter by class: --class 0, or --class 0 2 3')
    parser.add_argument('--agnostic-nms', action='store_true', help='class-agnostic NMS')
    parser.add_argument('--augment', action='store_true', help='augmented inference')
    parser.add_argument('--update', action='store_true', help='update all models')
    parser.add_argument('--project', default='runs/detect', help='save results to project/name')
    parser.add_argument('--name', default='object_tracking', help='save results to project/name')
    parser.add_argument('--exist-ok', action='store_true', help='existing project/name ok, do not increment')
    parser.add_argument('--no-trace', action='store_true', help='don`t trace model')
    parser.add_argument('--cropping', nargs='+', type=int,
                        help='crop image: --cropping x1 x2 y1 y2, eg: --cropping 0 640 0 480')
    parser.add_argument('--cam-fps', type=int, default=30, help='camera fps, eg: --cam-fps 30, default:25')
    parser.add_argument('--sensitivity', type=int, default=1,
                        help='sensitivity of the car stopping requirement as percent value, value between 0 and 100, 100 is full stop for 1 second default: 100')

    # Michael --Upload File

    parser.add_argument('--upload', action='store_true', help='Upload data to server')

    opt = parser.parse_args()
    print(opt)
    # check_requirements(exclude=('pycocotools', 'thop'))

    with torch.no_grad():
        if opt.update:  # update all models (to fix SourceChangeWarning)
            for opt.weights in ['yolov7.pt']:
                detect()
                strip_optimizer(opt.weights)
        else:
            detect()
