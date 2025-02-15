from ctypes import *
import math
import random
import os
import cv2
import time
import argparse

def sample(probs):
    s = sum(probs)
    probs = [a/s for a in probs]
    r = random.uniform(0, 1)
    for i in range(len(probs)):
        r = r - probs[i]
        if r <= 0:
            return i
    return len(probs)-1

def c_array(ctype, values):
    arr = (ctype*len(values))()
    arr[:] = values
    return arr

class BOX(Structure):
    _fields_ = [("x", c_float),
                ("y", c_float),
                ("w", c_float),
                ("h", c_float)]

class DETECTION(Structure):
    _fields_ = [("bbox", BOX),
                ("classes", c_int),
                ("prob", POINTER(c_float)),
                ("mask", POINTER(c_float)),
                ("objectness", c_float),
                ("sort_class", c_int)]


class IMAGE(Structure):
    _fields_ = [("w", c_int),
                ("h", c_int),
                ("c", c_int),
                ("data", POINTER(c_float))]

class METADATA(Structure):
    _fields_ = [("classes", c_int),
                ("names", POINTER(c_char_p))]

    

#lib = CDLL("/home/pjreddie/documents/darknet/libdarknet.so", RTLD_GLOBAL)
# lib = CDLL("libdarknet.so", RTLD_GLOBAL)
lib = CDLL(os.path.join(os.getcwd(), "libdarknet.so"), RTLD_GLOBAL)
lib.network_width.argtypes = [c_void_p]
lib.network_width.restype = c_int
lib.network_height.argtypes = [c_void_p]
lib.network_height.restype = c_int

predict = lib.network_predict
predict.argtypes = [c_void_p, POINTER(c_float)]
predict.restype = POINTER(c_float)

set_gpu = lib.cuda_set_device
set_gpu.argtypes = [c_int]

make_image = lib.make_image
make_image.argtypes = [c_int, c_int, c_int]
make_image.restype = IMAGE

get_network_boxes = lib.get_network_boxes
get_network_boxes.argtypes = [c_void_p, c_int, c_int, c_float, c_float, POINTER(c_int), c_int, POINTER(c_int)]
get_network_boxes.restype = POINTER(DETECTION)

make_network_boxes = lib.make_network_boxes
make_network_boxes.argtypes = [c_void_p]
make_network_boxes.restype = POINTER(DETECTION)

free_detections = lib.free_detections
free_detections.argtypes = [POINTER(DETECTION), c_int]

free_ptrs = lib.free_ptrs
free_ptrs.argtypes = [POINTER(c_void_p), c_int]

network_predict = lib.network_predict
network_predict.argtypes = [c_void_p, POINTER(c_float)]

reset_rnn = lib.reset_rnn
reset_rnn.argtypes = [c_void_p]

load_net = lib.load_network
load_net.argtypes = [c_char_p, c_char_p, c_int]
load_net.restype = c_void_p

do_nms_obj = lib.do_nms_obj
do_nms_obj.argtypes = [POINTER(DETECTION), c_int, c_int, c_float]

do_nms_sort = lib.do_nms_sort
do_nms_sort.argtypes = [POINTER(DETECTION), c_int, c_int, c_float]

free_image = lib.free_image
free_image.argtypes = [IMAGE]

letterbox_image = lib.letterbox_image
letterbox_image.argtypes = [IMAGE, c_int, c_int]
letterbox_image.restype = IMAGE

load_meta = lib.get_metadata
lib.get_metadata.argtypes = [c_char_p]
lib.get_metadata.restype = METADATA

load_image = lib.load_image_color
load_image.argtypes = [c_char_p, c_int, c_int]
load_image.restype = IMAGE

rgbgr_image = lib.rgbgr_image
rgbgr_image.argtypes = [IMAGE]

predict_image = lib.network_predict_image
predict_image.argtypes = [c_void_p, IMAGE]
predict_image.restype = POINTER(c_float)

def classify(net, meta, im):
    out = predict_image(net, im)
    res = []
    for i in range(meta.classes):
        res.append((meta.names[i], out[i]))
    res = sorted(res, key=lambda x: -x[1])
    return res

def detect(net, meta, image, thresh=.5, hier_thresh=.5, nms=.45):
    im = load_image(image, 0, 0)
    num = c_int(0)
    pnum = pointer(num)
    predict_image(net, im)
    dets = get_network_boxes(net, im.w, im.h, thresh, hier_thresh, None, 0, pnum)
    num = pnum[0]
    if (nms): do_nms_obj(dets, num, meta.classes, nms);

    res = []
    for j in range(num):
        for i in range(meta.classes):
            if dets[j].prob[i] > 0:
                b = dets[j].bbox
                res.append((meta.names[i], dets[j].prob[i], (b.x, b.y, b.w, b.h)))
    res = sorted(res, key=lambda x: -x[1])
    free_image(im)
    free_detections(dets, num)
    return res

# input : image path
# load pretrained weights, classes
counter=0


def localize(net,meta,image_path, output_folder):

	'''
	Function the localizes the objects present in the image and writed the images in output_folder
	parameters:
		net - is a load_net() function output
		meta - load_meta() function output
		image_path - Path of the image encoded in bytes
		output_folder - Path of folder where the input images need to plotted along with thier bounding boxes
	Output:
		predicted_class - Object classes present in the input image
		class_condifence - How much yolov3 is confidence about the classification
		bounding boxes - bounding boxes of all the objects present in the image 
		(top left x coordinate, top left y coordinate, bottom right x coordinate, bottom right y coordinate)
	'''

    t0=time.time()
    r=detect(net,meta,image_path.encode())
    print("fps:",(1/(time.time()-t0)))
    bounding_box=[]
    predicted_class=[]
    class_confidence=[]
    output=[]
    for i in range(len(r)):
        bbox=r[i][2]
        pred_class=r[i][0].decode()
        confidence=r[i][1]
        x1=int((bbox[0]-bbox[2]/2))
        y1=int((bbox[1]-bbox[3]/2))
        x2=int((bbox[0]+bbox[2]/2))
        y2=int((bbox[1]+bbox[3]/2))
        cv2.rectangle(image,(x1,y1),(x2,y2),(0,255,255),2)
        bounding_box.append([x1,y1,x2,y2])
        predicted_class.append(pred_class)
        class_confidence.append(confidence)
    cv2.imwrite(output_folder+str(counter)+'.jpg',image)
    counter+=1
    output.append([predicted_class,class_confidence,bounding_box])
    return output

    
if __name__ == "__main__":

    parser = argparse.ArgumentParser(description='Python YOLO v3')

    parser.add_argument('--dataset', dest='dataset', default="input_image/", help='dataset name')

    parser.add_argument('--output_folder',dest='output_folder',default="output_images/",help='output file name')

    args = parser.parse_args()

    net = load_net(b"cfg/yolov3.cfg", b"yolov3.weights", 0)
    meta = load_meta(b"cfg/coco.data")
    img_file=sorted(os.listdir(args.dataset))

    for img in img_file:
        image_data=args.dataset+img
        _=localize(net,meta,image_data, args.output_folder)


