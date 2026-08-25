---
layout: post
title:  "NCS2에서 YOLOv3가 실행되지 않을 때: FP16 IR 변환과 입력 Shape 점검"
summary: "라즈베리파이 3와 Neural Compute Stick 2에서 YOLO를 추론하기 위해 weights를 PB와 OpenVINO IR로 바꾸는 흐름을 정리합니다. FP16 지정, 416×416 입력, NHWC·NCHW 변환, MYRIAD 대상 설정에서 생기는 실패를 당시 코드 조각으로 짚습니다."
image:
  path: /assets/img/thumb/YOLOOpenvino.jpg
  alt: 라즈베리파이에서 Openvino 끄적이기 대표 이미지
date:   2019-03-30 13:00 -0400
categories: Basics
tags:
  - YOLO
  - 온디바이스AI
  - 컴퓨터비전
  - 경량화
  - 튜토리얼
---

NCS2에서 YOLO가 로드되지 않는다면 먼저 IR이 FP16으로 만들어졌는지, 모델 입력이 416×416인지, 애플리케이션이 MYRIAD 장치와 올바른 tensor 순서를 쓰는지 확인해야 합니다.

## YOLO 버전에 따라 변환 경로가 다르다

이 기록의 장비는 Raspberry Pi 3, Neural Compute Stick 2, webcam이며 OpenCV 4.0.0과 [OpenVINO 설치 과정](https://jjxxmiin.github.io/pi/2019/03/08/NCS2/)을 전제로 합니다. YOLOv3와 tiny 모델은 `tensorflow-yolo-v3` 변환기를, YOLOv1·v2는 `darkflow`를 거쳐 TensorFlow `.pb`를 만든 뒤 Model Optimizer로 IR을 생성합니다.

YOLOv3 경로에서 사용한 저장소와 고정 revision은 다음과 같습니다.

```bash
git clone https://github.com/mystic123/tensorflow-yolo-v3.git
cd tensorflow-yolo-v3
git checkout ed60b90
```

가중치와 class 이름은 원문의 [YOLOv3 weights](https://pjreddie.com/media/files/yolov3.weights), [YOLOv3-tiny weights](https://pjreddie.com/media/files/yolov3-tiny.weights), [coco.names](https://raw.githubusercontent.com/pjreddie/darknet/master/data/coco.names)를 사용합니다.

다음은 필요한 인자를 보여주는 당시 명령 조각입니다. 원문처럼 줄만 나눠 붙여 넣으면 별도 명령으로 해석되므로, 실제 실행 시 하나의 명령으로 연결하고 파일 위치와 의존성을 맞춰야 합니다.

```text
python convert_weights_pb.py
  --class_names coco.names
  --data_format NHWC
  --weights_file yolov3.weights
```

tiny 모델은 weight 파일을 `yolov3-tiny.weights`로 바꾸고 `--tiny`를 추가합니다. 생성된 graph summary에서 input을 확인한 뒤 IR 변환 인자를 정합니다.

![YOLO PB 그래프 입력 요약](/assets/img/post_img/intel/yolo_summary.PNG)

## IR 변환에서 FP16을 빼면 생기는 문제

YOLOv3의 Model Optimizer 호출에는 input shape, data type, YOLO custom operation 설정이 함께 필요합니다.

```text
python mo_tf.py
  --input_model yolov3.pb
  --input_shape [1,416,416,3]
  --data_type FP16
  --tensorflow_use_custom_operations_config extensions/front/tf/yolo_v3.json
```

이 역시 여러 줄 실행 스크립트가 아니라 인자 구조를 보여주는 핵심 조각입니다. 각 인자를 같은 `python mo_tf.py` 호출에 전달해야 합니다. graph summary의 batch가 `-1`이면 실제 추론용 batch와 공간 크기로 정해야 합니다.

이 기록의 NCS2 MYRIAD 대상은 FP32 IR을 지원하지 않아 `--data_type FP16`이 필수였습니다. 변환이 끝나면 같은 모델에서 나온 `.xml`과 `.bin`을 라즈베리파이로 함께 옮깁니다. YOLOv1·v2는 `darkflow`에서 `--savepb`로 PB를 만들고, `yolo_v1_v2.json` custom operation 설정을 사용하는 별도 경로입니다. 버전별 변환 파일을 섞지 않는 것이 중요합니다.

## OpenCV와 Inference Engine에서 확인할 입력

OpenCV DNN 경로의 핵심은 IR 두 파일을 함께 읽고 대상 장치를 MYRIAD로 지정하는 것입니다.

```python
net = cv.dnn.readNet(xml_path, bin_path)
net.setPreferableTarget(cv.dnn.DNN_TARGET_MYRIAD)

frame = cv.imread('test.jpeg')
frame = cv.resize(frame, (416, 416))
blob = cv.dnn.blobFromImage(frame, size=(416, 416), ddepth=cv.CV_8U)
net.setInput(blob)
out = net.forward()
```

이 조각은 forward 시간과 raw output을 얻는 부분까지만 포함합니다. YOLO box를 decoding하고 class 이름을 붙이는 완전한 검출 애플리케이션은 아닙니다.

당시 OpenVINO Inference Engine API에서는 `IENetwork`로 XML/BIN을 읽고 `IEPlugin(device='MYRIAD')`으로 로드했습니다. 이미지 배열은 batch 축을 더한 뒤 NHWC에서 NCHW로 순서를 바꿉니다.

```python
resized_image = cv.resize(frame, (416, 416), interpolation=cv.INTER_CUBIC)
prepimg = resized_image[np.newaxis, :, :, :]
prepimg = prepimg.transpose((0, 3, 1, 2))
res = exec_net.infer({'inputs': prepimg})
```

입력 이름 `inputs`는 원문 모델을 기준으로 합니다. 다른 graph라면 네트워크의 실제 input key와 output layer를 확인해야 합니다.

## 변환 성공과 실제 검출 성공을 구분하기

![NCS2 YOLO 추론 시간 출력](/assets/img/post_img/intel/inference.PNG)

원문에서는 OpenCV 경로의 첫 추론이 더 느려 보였지만 반복 실행에서는 두 방식의 시간 차이가 크지 않았습니다. 한 번의 숫자만으로 방식을 고르기보다 초기 호출과 반복 호출을 나눠 관찰할 필요가 있습니다.

실패를 좁힐 때는 다음 순서가 유용합니다.

- PB graph summary에서 input shape와 input 이름을 확인합니다.
- YOLO 버전에 맞는 custom operations JSON을 사용합니다.
- IR이 `FP16`인지, XML과 BIN이 같은 변환 결과인지 확인합니다.
- 애플리케이션의 resize 크기와 Model Optimizer의 shape를 맞춥니다.
- NHWC 입력을 NCHW로 옮겼는지 확인합니다.
- OpenCV 또는 Inference Engine의 target을 MYRIAD로 지정합니다.
- forward 결과만 얻은 코드를 완전한 box decoding 예제로 오해하지 않습니다.

이 글은 2019년 OpenVINO API와 특정 Git revision을 기록한 자료입니다. [YOLO 변환 참고 저장소](https://github.com/PINTO0309/OpenVINO-YoloV3)와 [당시 TensorFlow 변환 안내](https://software.intel.com/en-us/articles/OpenVINO-Using-TensorFlow#converting-a-darknet-yolo-model)를 해당 환경과 대조해 사용해야 하며, 게시된 조각만으로 설치부터 화면 출력까지 모두 실행된다고 가정하면 안 됩니다.
