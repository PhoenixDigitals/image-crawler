import os
import cv2
import argparse
import numpy as np
import tensorflow as tf
import six.moves.urllib as urllib
import tarfile

from utils.app_utils import FPS, WebcamVideoStream, HLSVideoStream
from object_detection.utils import label_map_util
from object_detection.utils import visualization_utils as vis_util


CWD_PATH = os.path.dirname(os.path.realpath(__file__))

# Path to frozen detection graph. This is the actual model that is used for the object detection.
# download from https://github.com/tensorflow/models/blob/master/research/object_detection/g3doc/detection_model_zoo.md
MODEL_NAME = 'ssd_mobilenet_v2_coco_2018_03_29'
#MODEL_NAME = 'ssd_mobilenet_v1_coco_11_06_2017' #fast
#MODEL_NAME = 'faster_rcnn_resnet101_kitti_2018_01_28'
#MODEL_NAME = 'faster_rcnn_resnet101_coco_11_06_2017' #medium speed
#MODEL_NAME = 'faster_rcnn_nas_coco_2018_01_28'
#MODEL_NAME = 'ssdlite_mobilenet_v2_coco_2018_05_09'

MODEL_FILE = MODEL_NAME + '.tar.gz'
PATH_TO_MODELS =os.path.join(CWD_PATH, "model")
PATH_TO_CKPT = os.path.join(PATH_TO_MODELS, MODEL_NAME, 'frozen_inference_graph.pb')
PATH_TO_LABELS = os.path.join(CWD_PATH, 'object_detection', 'data', 'mscoco_label_map.pbtxt')
PATH_TO_TGZ = os.path.join(PATH_TO_MODELS, MODEL_FILE)
NUM_CLASSES = 90


DOWNLOAD_BASE = 'http://download.tensorflow.org/models/object_detection/'
fileAlreadyExists = os.path.isfile(PATH_TO_CKPT)
if not fileAlreadyExists:
    download_url =DOWNLOAD_BASE + MODEL_FILE
    print('Downloading frozen inference graph: '+download_url)
    opener = urllib.request.URLopener()
    opener.retrieve(download_url, PATH_TO_TGZ)
    tar_file = tarfile.open(PATH_TO_TGZ)
    tar_file.extractall(path= PATH_TO_MODELS)


NUM_CLASSES = 90

# Loading label map
label_map = label_map_util.load_labelmap(PATH_TO_LABELS)
categories = label_map_util.convert_label_map_to_categories(label_map, max_num_classes=NUM_CLASSES,
                                                            use_display_name=True)
category_index = label_map_util.create_category_index(categories)


def detect_objects(image_np, sess, detection_graph):
    # Expand dimensions since the model expects images to have shape: [1, None, None, 3]
    image_np_expanded = np.expand_dims(image_np, axis=0)
    image_tensor = detection_graph.get_tensor_by_name('image_tensor:0')

    # Each box represents a part of the image where a particular object was detected.
    boxes = detection_graph.get_tensor_by_name('detection_boxes:0')

    # Each score represent how level of confidence for each of the objects.
    # Score is shown on the result image, together with the class label.
    scores = detection_graph.get_tensor_by_name('detection_scores:0')
    classes = detection_graph.get_tensor_by_name('detection_classes:0')
    num_detections = detection_graph.get_tensor_by_name('num_detections:0')

    # Actual detection.
    (boxes, scores, classes, num_detections) = sess.run(
        [boxes, scores, classes, num_detections],
        feed_dict={image_tensor: image_np_expanded})

    sboxes = np.squeeze(boxes)
    sboxes = sboxes[~np.all(sboxes == 0, axis=1)]
    box = tuple(sboxes[0].tolist())

    # Visualization of the results of a detection.
    vis_util.visualize_boxes_and_labels_on_image_array(
        image_np,
        np.squeeze(boxes),
        np.squeeze(classes).astype(np.int32),
        np.squeeze(scores),
        category_index,
        use_normalized_coordinates=True,
        line_thickness=8)
    return image_np


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-src', '--source', dest='video_source', type=int,
                        default=0, help='Device index of the camera.')
    parser.add_argument('-wd', '--width', dest='width', type=int,
                        default=480, help='Width of the frames in the video stream.')
    parser.add_argument('-ht', '--height', dest='height', type=int,
                        default=360, help='Height of the frames in the video stream.')
    args = parser.parse_args()

    # Load a (frozen) Tensorflow model into memory.
    print("Loading tensorflow model.")
    detection_graph = tf.Graph()
    with detection_graph.as_default():
        od_graph_def = tf.GraphDef()
        with tf.gfile.GFile(PATH_TO_CKPT, 'rb') as fid:
            serialized_graph = fid.read()
            od_graph_def.ParseFromString(serialized_graph)
            tf.import_graph_def(od_graph_def, name='')

        sess = tf.Session(graph=detection_graph)

    print('Reading from webcam.')
    video_capture = WebcamVideoStream(src=args.video_source,
                                      width=args.width,
                                      height=args.height).start()

    while True:
        frame = video_capture.read()
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        frame_detected = detect_objects(frame_rgb, sess, detection_graph)

        output_rgb = cv2.cvtColor(frame_detected, cv2.COLOR_RGB2BGR)
        cv2.imshow('Video', output_rgb)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    sess.close()
    video_capture.stop()
    cv2.destroyAllWindows()