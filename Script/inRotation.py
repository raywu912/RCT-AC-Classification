import os
import cv2
import numpy as np
import mediapipe as mp
import math

from constant import POSE
from featureUtils import Utils

# Mediapipe - Holistic
mp_drawing = mp.solutions.drawing_utils
mp_drawing_styles = mp.solutions.drawing_styles
mp_holistic = mp.solutions.holistic

# path = "/Users/ray/Thesis/Input/test/"
path = "/Users/ray/Thesis/Shoulder/Internal Rotation_120/"
allFileList = sorted(os.listdir(path))

# Create the empty list to contain all feature by each patient
allFeature = np.empty((0,189), float)

# Traversal files of folder
for fileName in allFileList:
  
  holistic = mp_holistic.Holistic(
    static_image_mode=False,
    model_complexity=2,
    enable_segmentation=True,
    min_detection_confidence=0.5,
    min_tracking_confidence=0.5)

  continueProc = False
  if not fileName.startswith('.') and os.path.isfile(os.path.join(path, fileName)):
    
    # Check files name "Special" markers
    if "*" in fileName: # Check for problem video
      continue

    if fileName.split('_')[1] == 'R':
      side = 'right_'
    else:
      side = 'left_'

    wrist = POSE[side+'wrist']
    elbow = POSE[side+'elbow']
    shoulder = POSE[side+'shoulder']
    hip = POSE[side+'hip']

    # Read Video
    inputVideo = cv2.VideoCapture(path+fileName)
    print(fileName)
    fps = inputVideo.get(cv2.CAP_PROP_FPS)

    # Check the direction of video by first input image
    direction = 'normal'

    success, image = inputVideo.read()
    results = holistic.process(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
    X = Y = np.array([])
    for _, landmarks in enumerate(results.pose_landmarks.landmark):
            X = np.append(X, landmarks.x)
            Y = np.append(Y, landmarks.y)
    if Y[hip] < Y[shoulder]:
      direction = 'flip'
    # elif X[hip]*1.5 > X[shoulder]:
    #   direction = 'left_rotation'
    # elif X[hip]*1.5 < X[shoulder]:
    #   direction = 'right_rotation'

    countFrames = 0
    
    utils = Utils()

    holistic = mp_holistic.Holistic(
    static_image_mode=False,
    model_complexity=2,
    enable_segmentation=True,
    min_detection_confidence=0.5,
    min_tracking_confidence=0.5)

    # Read Video & Get Position 
    while success:
      success, image = inputVideo.read()
      if direction == 'flip':
        image = cv2.flip(image, -1)
      elif direction == 'left_rotation':
        image = cv2.rotate(image, cv2.ROTATE_90_CLOCKWISE)
      elif direction == 'right_rotation':
        image = cv2.rotate(image, cv2.ROTATE_90_COUNTERCLOCKWISE)

      if success == True:
        results = holistic.process(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))

        # Draw landmarks on Pic.
        # mp_drawing.draw_landmarks(
        #   image,
        #   results.pose_landmarks,
        #   mp_holistic.POSE_CONNECTIONS,
        #   landmark_drawing_spec=mp_drawing_styles
        #   .get_default_pose_landmarks_style())
        # cv2.imwrite("/Users/ray/Thesis/Input/output/"+str(fileName[0:5])+str(countFrames)+".jpg", image)

        # Get Position of Each Frame
        utils.getPosition(results)
        
        countFrames += 1
        continueProc = True
      else:
        break
    
  ##### The Position Feature #####
  if continueProc == True:
    # Start Position
    # Find the Lowest Position of All Frame in First Seconds.
    startFrame = utils.getStartPosition(utils.PositionY[0:30, wrist], mType='min')

    # End Position
    stbEndFrame = utils.getEndPosition(utils.PositionX[30:, wrist],
                                       utils.PositionY[30:, wrist],
                                       mType='max') # Keep detecting highest point
    
    # Reduce Data Size -> normalize to 100 Frames
    StartEndFrames = stbEndFrame - startFrame
    if StartEndFrames >= 60:
      splitList = utils.splitFrames(StartEndFrames, 59)
      splitList = np.insert(splitList, 0, startFrame)

      timeOfNormalize = (StartEndFrames/fps)/len(splitList) # Start-End Duration Time

      count = 0
      numOfFrame = 0

      for i in splitList:
        count += 1
        numOfFrame += i
        ### Processing Feature Extraction from 60-Selected Frames ###
        utils.landmarkDisplacement(startFrame, utils.PositionX[numOfFrame], utils.PositionY[numOfFrame], shoulder, wrist)
        
        currentElbow = [utils.PositionX[numOfFrame][elbow], utils.PositionY[numOfFrame][elbow]]
        currentWrist = [utils.PositionX[numOfFrame][wrist], utils.PositionY[numOfFrame][wrist]]
        currentVec = utils.getVector(currentElbow, currentWrist)

        angleReverse = False
        if (count<=10) and (currentWrist[1] < currentElbow[1]):
          angleReverse = True

        if side == 'right_':
          utils.getHorzVertAngle([1, 0], currentVec, angleReverse)
        elif side == 'left_':
          utils.getHorzVertAngle([-1, 0], currentVec, angleReverse)
          
        # Type of Variation features
        if count%15 == 0:
          # Get Speed
          utils.getAngularVelocity(utils.motionAngle[count-15], utils.motionAngle[count-1], timeOfNormalize*14, (count/15)-1)

      print(f"Start: {startFrame}, End: {stbEndFrame}, Max Angle: {utils.motionAngle[59]}")
      
      # Combine All Feature
      featureTmp = np.hstack((fileName[0:5],
                              utils.shoulderDisplacement, utils.elbowDisplacement,
                              utils.motionAngle,
                              utils.angularVelocity, utils.angularAcceleration))
      allFeature = np.append(allFeature, [featureTmp], axis=0)


headerLsit60 = ['ShoulderDisplacement', 'ElbowDisplacement', 'MotionAngle']
headerLsit4 = ['AngularVelocity','AngularAcceleration']
header = 'ID,'
header += ','.join(s+str(i) for s in headerLsit60 for i in range(60)) + ','
header += ','.join(s+str(i) for s in headerLsit4 for i in range(4))
  
np.savetxt("inRotation_HC.csv", allFeature, fmt="%s", delimiter=",", header=header)