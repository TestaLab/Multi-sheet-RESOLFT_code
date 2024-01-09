#include <stdint.h>
#include <Arduino.h>
#include "parameters.h"

//GLOBAL PARAMETER INITIALIZATION

//DAC RASTER SCAN
uint8_t dimOneChan = 0;
float dimOneStartV = 0; //In volts
float dimOneLenV = 0;
float dimOneStepSizeV = 0;
uint8_t dimTwoChan = 0;
float dimTwoStartV = 0;
float dimTwoLenV = 0;
float dimTwoStepSizeV = 0;
uint8_t dimThreeChan = 0;
float dimThreeStartV = 0;
float dimThreeLenV = 0;
float dimThreeStepSizeV = 0;
uint8_t dimFourChan = 0;
float dimFourStartV = 0;
float dimFourLenV = 0;
float dimFourStepSizeV = 0;
float angleRad = 0;

//DAC pLS-RESOLFT SCAN
uint8_t onLaserTTLChan = 0;
uint8_t offLaserTTLChan = 0;
uint8_t roLaserTTLChan = 0;
uint8_t roScanDACChan = 0;
uint8_t cycleScanDACChan = 0;

uint16_t timeLapsePoints = 0;
uint32_t timeLapseDelayUs = 0;
uint32_t delayBeforeOnUs = 0;
uint32_t onPulseTimeUs = 0;
uint32_t delayAfterOnUs = 0;
uint32_t offPulseTimeUs = 0;
uint32_t delayAfterOffUs = 0;
uint32_t delayAfterDACStepUs = 0;
uint32_t roPulseTimeUs = 0;
uint32_t delayAfterRoUs = 0;
float roRestingV = 0;
float roStartV = 0;
float roStepSizeV = 0;
uint32_t roSteps = 0;
float cycleStartV = 0;
float cycleStepSizeV = 0;
uint32_t cycleSteps = 0;

//PIXEL CYCLE PARAMETERS, CURRENTLY FOR UP TO 3 PULSES
uint32_t sequenceTimeUs = 0;
uint8_t p1Line = 0;
uint32_t p1StartUs = 0;
uint32_t p1EndUs = 0;
uint8_t p2Line = 0;
uint32_t p2StartUs = 0;
uint32_t p2EndUs = 0;
uint8_t p3Line = 0;
uint32_t p3StartUs = 0;
uint32_t p3EndUs = 0;

void readParameter(String & inputString) {
  String out = "Running read parameter function";
  Serial.println(out);
  //Function to read paramter sent on form "PARAMETER,pName,pType,pValue\n"
  byte charPos = 10;
  String pName = "";
  while (inputString[charPos] != ',' && inputString[charPos] != '\n' )
  {
    while (inputString[charPos] == ' ') {
      charPos++;
    }//Skip white spaces
    pName += (char)inputString[charPos];
    charPos++;
  }

  //Skip commma
  charPos++;
  String pValue = "";
  while (inputString[charPos] != ',' && inputString[charPos] != '\n' )
  {
    while (inputString[charPos] == ' ') {
      charPos++;
    }//Skip white spaces
    pValue += (char)inputString[charPos];
    charPos++;
  }
  out = "Recieved pName: " + pName + ", pValue: " + pValue;
  Serial.println(out);
  setParameter(pName, pValue);//Send extracted strings to setParameter function
}

void setParameter(String pName, String pValue)
{
  String debugOut;
  //DAC RASTER SCAN
  if (pName == "dimOneChan") {
    dimOneChan = pValue.toInt();
    debugOut = "Parameter " + pName + " set to " + (String)dimOneChan;
  }
  if (pName == "dimOneStartV") {
    dimOneStartV = pValue.toFloat();
    debugOut = "Parameter " + pName + " set to " + (String)dimOneStartV;
  }
  if (pName == "dimOneLenV") {
    dimOneLenV = pValue.toFloat();
    debugOut = "Parameter " + pName + " set to " + (String)dimOneLenV;
  }
  if (pName == "dimOneStepSizeV") {
    dimOneStepSizeV = pValue.toFloat();
    debugOut = "Parameter " + pName + " set to " + (String)dimOneStepSizeV;
  }
  if (pName == "dimTwoChan") {
    dimTwoChan = pValue.toInt();
    debugOut = "Parameter " + pName + " set to " + (String)dimTwoChan;
  }
  if (pName == "dimTwoStartV") {
    dimTwoStartV = pValue.toFloat();
    debugOut = "Parameter " + pName + " set to " + (String)dimTwoStartV;
  }
  if (pName == "dimTwoLenV") {
    dimTwoLenV = pValue.toFloat();
    debugOut = "Parameter " + pName + " set to " + (String)dimTwoLenV;
  }
  if (pName == "dimTwoStepSizeV") {
    dimTwoStepSizeV = pValue.toFloat();
    debugOut = "Parameter " + pName + " set to " + (String)dimTwoStepSizeV;
  }
  if (pName == "dimThreeChan") {
    dimThreeChan = pValue.toInt();
    debugOut = "Parameter " + pName + " set to " + (String)dimThreeChan;
  }
  if (pName == "dimThreeStartV") {
    dimThreeStartV = pValue.toFloat();
    debugOut = "Parameter " + pName + " set to " + (String)dimThreeStartV;
  }
  if (pName == "dimThreeLenV") {
    dimThreeLenV = pValue.toFloat();
    debugOut = "Parameter " + pName + " set to " + (String)dimThreeLenV;
  }
  if (pName == "dimThreeStepSizeV") {
    dimThreeStepSizeV = pValue.toFloat();
    debugOut = "Parameter " + pName + " set to " + (String)dimThreeStepSizeV;
  }
  if (pName == "dimFourChan") {
    dimFourChan = pValue.toInt();
    debugOut = "Parameter " + pName + " set to " + (String)dimFourChan;
  }
  if (pName == "dimFourStartV") {
    dimFourStartV = pValue.toFloat();
    debugOut = "Parameter " + pName + " set to " + (String)dimFourStartV;
  }
  if (pName == "dimFourLenV") {
    dimFourLenV = pValue.toFloat();
    debugOut = "Parameter " + pName + " set to " + (String)dimFourLenV;
  }
  if (pName == "dimFourStepSizeV") {
    dimFourStepSizeV = pValue.toFloat();
    debugOut = "Parameter " + pName + " set to " + (String)dimFourStepSizeV;
  }
  if (pName == "angleRad") {
    angleRad = pValue.toFloat();
    debugOut = "Parameter " + pName + " set to " + (String)angleRad;
  }
  
  //DAC pLS-RESOLFT SCAN
  if (pName == "onLaserTTLChan") {
    onLaserTTLChan = pValue.toInt();
    debugOut = "Parameter " + pName + " set to " + (String)onLaserTTLChan;
  }
  if (pName == "offLaserTTLChan") {
    offLaserTTLChan = pValue.toInt();
    debugOut = "Parameter " + pName + " set to " + (String)offLaserTTLChan;
  }
  if (pName == "roLaserTTLChan") {
    roLaserTTLChan = pValue.toInt();
    debugOut = "Parameter " + pName + " set to " + (String)roLaserTTLChan;
  }
  if (pName == "roScanDACChan") {
    roScanDACChan = pValue.toInt();
    debugOut = "Parameter " + pName + " set to " + (String)roScanDACChan;
  }
  if (pName == "cycleScanDACChan") {
    cycleScanDACChan = pValue.toInt();
    debugOut = "Parameter " + pName + " set to " + (String)cycleScanDACChan;
  }
  if (pName == "timeLapsePoints") {
    timeLapsePoints = pValue.toInt();
    debugOut = "Parameter " + pName + " set to " + (String)timeLapsePoints;
  }
  if (pName == "timeLapseDelayUs") {
    timeLapseDelayUs = pValue.toInt();
    debugOut = "Parameter " + pName + " set to " + (String)timeLapseDelayUs;
  }
  if (pName == "delayBeforeOnUs") {
    delayBeforeOnUs = pValue.toInt();
    debugOut = "Parameter " + pName + " set to " + (String)delayBeforeOnUs;
  }
  if (pName == "onPulseTimeUs") {
    onPulseTimeUs = pValue.toInt();
    debugOut = "Parameter " + pName + " set to " + (String)onPulseTimeUs;
  }
  if (pName == "delayAfterOnUs") {
    delayAfterOnUs = pValue.toInt();
    debugOut = "Parameter " + pName + " set to " + (String)delayAfterOnUs;
  }
  if (pName == "offPulseTimeUs") {
    offPulseTimeUs = pValue.toInt();
    debugOut = "Parameter " + pName + " set to " + (String)offPulseTimeUs;
  }
  if (pName == "delayAfterOffUs") {
    delayAfterOffUs = pValue.toInt();
    debugOut = "Parameter " + pName + " set to " + (String)delayAfterOffUs;
  }
  if (pName == "delayAfterDACStepUs") {
    delayAfterDACStepUs = pValue.toInt();
    debugOut = "Parameter " + pName + " set to " + (String)delayAfterDACStepUs;
  }
  if (pName == "roPulseTimeUs") {
    roPulseTimeUs = pValue.toInt();
    debugOut = "Parameter " + pName + " set to " + (String)roPulseTimeUs;
  }
  if (pName == "delayAfterRoUs") {
    delayAfterRoUs = pValue.toInt();
    debugOut = "Parameter " + pName + " set to " + (String)delayAfterRoUs;
  }
  if (pName == "roRestingV") {
    roRestingV = pValue.toFloat();
    debugOut = "Parameter " + pName + " set to " + (String)roRestingV;
  }
  if (pName == "roStartV") {
    roStartV = pValue.toFloat();
    debugOut = "Parameter " + pName + " set to " + (String)roStartV;
  }
  if (pName == "roStepSizeV") {
    roStepSizeV = pValue.toFloat();
    debugOut = "Parameter " + pName + " set to " + (String)roStepSizeV;
  }
  if (pName == "roSteps") {
    roSteps = pValue.toInt();
    debugOut = "Parameter " + pName + " set to " + (String)roSteps;
  }
  if (pName == "cycleStartV") {
    cycleStartV = pValue.toFloat();
    debugOut = "Parameter " + pName + " set to " + (String)cycleStartV;
  }
  if (pName == "cycleStepSizeV") {
    cycleStepSizeV = pValue.toFloat();
    debugOut = "Parameter " + pName + " set to " + (String)cycleStepSizeV;
  }
  if (pName == "cycleSteps") {
    cycleSteps = pValue.toInt();
    debugOut = "Parameter " + pName + " set to " + (String)cycleSteps;
  }
  
  //PIXEL CYCLE PARAMETERS, CURRENTLY FOR UP TO 3 PULSES
  if (pName == "sequenceTimeUs") {
    sequenceTimeUs = pValue.toInt();
    debugOut = "Parameter " + pName + " set to " + (String)sequenceTimeUs;
  }
  if (pName == "p1Line") {
    p1Line = pValue.toInt();
    debugOut = "Parameter " + pName + " set to " + (String)p1Line;
  }
  if (pName == "p1StartUs") {
    p1StartUs = (uint16_t)pValue.toInt();
    debugOut = "Parameter " + pName + " set to " + (String)p1StartUs;
  }
  if (pName == "p1EndUs") {
    p1EndUs = (uint16_t)pValue.toInt();
    debugOut = "Parameter " + pName + " set to " + (String)p1EndUs;
  }
  if (pName == "p2Line") {
    p2Line = (uint8_t)pValue.toInt();
    debugOut = "Parameter " + pName + " set to " + (String)p2Line;
  }
  if (pName == "p2StartUs") {
    p2StartUs = (uint16_t)pValue.toInt();
    debugOut = "Parameter " + pName + " set to " + (String)p2StartUs;
  }
  if (pName == "p2EndUs") {
    p2EndUs = (uint16_t)pValue.toInt();
    debugOut = "Parameter " + pName + " set to " + (String)p2EndUs;
  }
  if (pName == "p3Line") {
    p3Line = (uint8_t)pValue.toInt();
    debugOut = "Parameter " + pName + " set to " + (String)p3Line;
  }
  if (pName == "p3StartUs") {
    p3StartUs = (uint16_t)pValue.toInt();
    debugOut = "Parameter " + pName + " set to " + (String)p3StartUs;
  }
  if (pName == "p3EndUs") {
    p3EndUs = (uint16_t)pValue.toInt();
    debugOut = "Parameter " + pName + " set to " + (String)p3EndUs;
  }
  Serial.println(debugOut);
}
