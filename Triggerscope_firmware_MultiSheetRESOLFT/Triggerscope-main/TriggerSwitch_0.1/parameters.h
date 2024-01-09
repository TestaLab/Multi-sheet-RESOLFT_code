#ifndef PARAMETERS_H
#define PARAMETERS_H

#include <stdint.h>
#include <Arduino.h>
//GLOBAL PARAMETER INITIALIZATION

//DAC RASTER SCAN
extern uint8_t dimOneChan;
extern float dimOneStartV; //In volts
extern float dimOneLenV;
extern float dimOneStepSizeV;
extern uint8_t dimTwoChan;
extern float dimTwoStartV;
extern float dimTwoLenV;
extern float dimTwoStepSizeV;
extern uint8_t dimThreeChan;
extern float dimThreeStartV;
extern float dimThreeLenV;
extern float dimThreeStepSizeV;
extern uint8_t dimFourChan;
extern float dimFourStartV;
extern float dimFourLenV;
extern float dimFourStepSizeV;
extern float angleRad;

//DAC pLS-RESOLFT SCAN
extern uint8_t onLaserTTLChan;
extern uint8_t offLaserTTLChan;
extern uint8_t roLaserTTLChan;
extern uint8_t roScanDACChan;
extern uint8_t cycleScanDACChan;

extern uint16_t timeLapsePoints;
extern uint32_t timeLapseDelayUs;
extern uint32_t delayBeforeOnUs;
extern uint32_t onPulseTimeUs;
extern uint32_t delayAfterOnUs;
extern uint32_t offPulseTimeUs;
extern uint32_t delayAfterOffUs;
extern uint32_t delayAfterDACStepUs;
extern uint32_t roPulseTimeUs;
extern uint32_t delayAfterRoUs;
extern float roRestingV;
extern float roStartV;
extern float roStepSizeV;
extern uint32_t roSteps;
extern float cycleStartV;
extern float cycleStepSizeV;
extern uint32_t cycleSteps;

//PIXEL CYCLE PARAMETERS, CURRENTLY FOR UP TO 3 PULSES
extern uint32_t sequenceTimeUs;
extern uint8_t p1Line;
extern uint32_t p1StartUs;
extern uint32_t p1EndUs;
extern uint8_t p2Line;
extern uint32_t p2StartUs;
extern uint32_t p2EndUs;
extern uint8_t p3Line;
extern uint32_t p3StartUs;
extern uint32_t p3EndUs;


//FUNCTIONS
void readParameter(String&);
void setParameter(String, String);

#endif
