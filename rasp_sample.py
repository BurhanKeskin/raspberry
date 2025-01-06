import os
from collections import defaultdict, deque

import cv2
import numpy as np
from ultralytics import YOLO

import supervision as sv

SOURCE = np.array([[738, 534], [1040, 534], [1428, 1079], [448, 1079]])

TARGET_WIDTH = 3.5
TARGET_HEIGHT = 140

TARGET = np.array(
    [
        [0, 0],
        [TARGET_WIDTH - 1, 0],
        [TARGET_WIDTH - 1, TARGET_HEIGHT - 1],
        [0, TARGET_HEIGHT - 1],
    ]
)

class ViewTransformer:
    def __init__(self, source: np.ndarray, target: np.ndarray) -> None:
        source = source.astype(np.float32)
        target = target.astype(np.float32)
        self.m = cv2.getPerspectiveTransform(source, target)

    def transform_points(self, points: np.ndarray) -> np.ndarray:
        if points.size == 0:
            return points
        reshaped_points = points.reshape(-1, 1, 2).astype(np.float32)
        transformed_points = cv2.perspectiveTransform(reshaped_points, self.m)
        return transformed_points.reshape(-1, 2)

if __name__ == "__main__":
    
    source_video_path = f"/home/{os.getlogin()}/speed_estimation/raspberry/rasp_sample.mp4"
    target_video_path = f"/home/{os.getlogin()}/speed_estimation/raspberry/output/isuzu.mp4"
    model_id = "yolov8x-640"
    confidence_threshold = 0.3
    iou_threshold = 0.7
    speed_limit = 95  # km/h, belirlenen hız sınırı

    video_info = sv.VideoInfo.from_video_path(video_path=source_video_path)
    model = YOLO("yolov8n.pt")

    byte_track = sv.ByteTrack(
        frame_rate=video_info.fps, track_activation_threshold=confidence_threshold
    )

    thickness = sv.calculate_optimal_line_thickness(
        resolution_wh=video_info.resolution_wh
    )

    text_scale = sv.calculate_optimal_text_scale(resolution_wh=video_info.resolution_wh)

    box_annotator = sv.BoxAnnotator(thickness=thickness)

    label_annotator = sv.LabelAnnotator(
        text_scale=text_scale,
        text_thickness=thickness,
        text_position=sv.Position.BOTTOM_CENTER,
    )
    trace_annotator = sv.TraceAnnotator(
        thickness=thickness,
        trace_length=video_info.fps * 2,
        position=sv.Position.BOTTOM_CENTER,
    )

    frame_generator = sv.get_video_frames_generator(source_path=source_video_path)

    polygon_zone = sv.PolygonZone(polygon=SOURCE)

    view_transformer = ViewTransformer(source=SOURCE, target=TARGET)

    coordinates = defaultdict(lambda: deque(maxlen=video_info.fps))
    
    processed_violations = set()  

    with sv.VideoSink(target_video_path, video_info) as sink:
        for frame_number, frame in enumerate(frame_generator):
            results = model(frame)[0]
            detections = sv.Detections.from_ultralytics(results)
            detections = detections[detections.confidence > confidence_threshold]
            detections = detections[polygon_zone.trigger(detections)]
            detections = detections.with_nms(threshold=iou_threshold)
            detections = byte_track.update_with_detections(detections=detections)

            points = detections.get_anchors_coordinates(
                anchor=sv.Position.BOTTOM_CENTER
            )

            points = view_transformer.transform_points(points=points).astype(int)

            for tracker_id, [_, y] in zip(detections.tracker_id, points):
                coordinates[tracker_id].append(y)

            labels = []

            for tracker_id in detections.tracker_id:
                if len(coordinates[tracker_id]) < video_info.fps / 2:
                    labels.append("")
                else:
                    coordinate_start = coordinates[tracker_id][-1]
                    coordinate_end = coordinates[tracker_id][0]
                    distance = abs(coordinate_start - coordinate_end)
                    time = len(coordinates[tracker_id]) / video_info.fps
                    speed = distance / time * 3.6

                    speed_label = f"{int(speed)} km/h"
                    labels.append(speed_label) 

                    if speed > speed_limit and tracker_id not in processed_violations:
                        x1, y1, x2, y2 = detections.xyxy[0]
                        cropped_frame = frame[int(y1)-50:int(y2)+50, int(x1)-50:int(x2)+50]
                        image_path = f"violations/vehicle_{tracker_id}_frame_{frame_number}.jpg"
                        os.makedirs("violations", exist_ok=True)
                        cv2.imwrite(image_path, cropped_frame)

                        processed_violations.add(tracker_id)

            annotated_frame = frame.copy()
            annotated_frame = trace_annotator.annotate(
                scene=annotated_frame, detections=detections
            )
            annotated_frame = box_annotator.annotate(
                scene=annotated_frame, detections=detections
            )
            annotated_frame = label_annotator.annotate(
                scene=annotated_frame, detections=detections, labels=labels
            )

            sink.write_frame(annotated_frame)
