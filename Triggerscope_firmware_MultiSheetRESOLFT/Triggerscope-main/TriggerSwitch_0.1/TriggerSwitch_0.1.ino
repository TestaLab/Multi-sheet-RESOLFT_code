
/******************************************/
/*Trigger Scope v. 200 for Arduino microscope control by
  ADVANCED RESEARCH CONSULTING @ 2015
  for info contact Austin Blanco
  austin@austinblanco.com c. 510-708-2995

  V612-ts4 changes
  - addressed char readin of data from SD card
  - replaced var type for RANGE DAC assignment & TRIG line assignment for suppoprting SD access( non const)
  - Added RESET Command to serial-reboot board.
  -

  TODO:
  -data card readin is OK but needs to be a tre ascii/dec conversion.


*/

/*****************************
  Contact Advanced Research Consulting for Driver libraries! www.advancedresearch.comsulting
 ******************************/


/*Firmware has been modified by Andreas Bodén */

#include <SD.h>
#include <SPI.h>
//#include <i2c_driver_wire.h>
#include <Wire.h>
#include "Linduino.h"
#include "Adafruit_MCP23017.h"

#include "parameters.h"

#define focus 15     //sets focus line #
#define pwrLed 11    //POWER indication
#define dacLed 12    //POWER indication
#define ttlLed 13    //POWER indication
#define trigLed 14   //POWER indication
#define readyLed 15  //POWER indication
#define initDACRange 2 //Default DAC range
#define ttlblock2OE 10
#define ttlblock2DIR 8
#define ttlblock1OE 9
#define ttlblock1DIR 7

File myFile; //create settings file
const int chipSelect = BUILTIN_SDCARD; //set SD card access CS line

Adafruit_MCP23017 mcp; //create mux object
//set up menu modes and vars
volatile int vOut = 0;      //voltage output digital value - change this to change the voltage output on the analog BNC
boolean trigArmed = false;  //enables while loop for just the high speed trig sequencing
unsigned long debugT = 0;   //debugger flag - not used in a few versions
unsigned long trigInterval; //tracks frequency of inputs from camera or external source
int trigStep = 0;           //optionally used to sequence more than 1 PROG line at a time, not fully implemented
String inputString = "";         // a string to hold incoming data
boolean stringComplete = false;  // whether the string is complete

//PIN ASSIGNMENTS
const byte DAC[16] = {0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15}; //MOVE THESE FOR CUSTOMERS IF NEEDED!
byte ttl[16] = {5, 6, 7, 8, 14, 15, 16, 17, 20, 0, 1, 2, 3, 4, 5, 6}; //ttl pin #'s (NOTE PINS 10-16 = GPIO
byte trig[4] = {0, 1, 2, 3};

//HIGH SPEED PROGRAMMING MODE MEMORY BLOCK
int     wArray[32767] = {};  //Arbitrary wave definer
int     tArray[32767] = {};  //Arbitrary wave definer
int     dacArray[1200][16] = {{0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0}}; // DACprogram list
boolean ttlArray[500][16] = {{0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0}}; // TTL program list
int     delArray[500]; //time delay array for high speed sequences
int     focArray[6]; //array for focus stacks = start, step, #loops,direction,slave,current step
int    waveArray[2][8] = {{0, 0, 0, 0, 0, 0, 0, 0}}; //wave function generator, see PROG_WAVE for details
uint16_t ttlActive = 0;
int timeCycles = 1; //used for high speed switching inside of a loop
int runCycles = 0; //holds running position vs total cycles for timelapse

//Memory arrays for DAC channels
int currentDACValues[16]; //these store the DAC assigned numbers!
byte RNG[16]; //these store the range choices for each channel
float VMin[16]; //Stores the min voltage of the range choosen
float VMax[16]; //Stores the max voltage of the range choosen

byte TRG[4] = {4, 4, 4, 4}; //trigger state saves 0 = LOW 1 = HIGH 2 = RISING 3 = FALLING 4 = CHANGE

volatile boolean inTrigger = false;
volatile boolean tState = false; //Martyn Addition
unsigned long timeOut = 5000; //timeout for sequence (set to 10 seconds by default)
unsigned long tLed = 0;
volatile boolean indicatorChange = 0; //a time tracker for LED status indications
boolean runonce = false; //Martyn addition
byte program = 0; //this sets the active program # used in the Mode 3 high speed sequencer
byte maxProgram = 0; //this holds the maximum program value entered, and is used to set the maxium sequence step.
byte stepMode = 1; //1 = waits for TTL IN, 2=runs continually
unsigned long tStart = 0; //sequence start timer
unsigned long trigLedTimer = 0;
boolean reportTime = 0;
boolean umArmIgnore = 0; //this handles micromanagers multiple ARM commands which are issued back-to-back on MDA acqtivation. Ignores after a short wait.
boolean usepwm = false;
byte pChannel = 0; //number of channels micromanager has attempted to control
String idname = "ARC TRIGGERSCOPE 16 R4 BOARD 4v.612F - TestaLab version";


//Timing variables
elapsedMicros sincePixelCycleStart;
elapsedMicros sincepLSRevent;

void setup() {
  mcp.begin(0x27);   //turn on MUX comms
  //Wire.setClock(1100000);
  for (int i = 0; i < 16; ++i) { //configure MCP pins as outputs
    mcp.pinMode(i, OUTPUT);
    mcp.digitalWrite(i, LOW);
  }

  //configure TTL outputs 5-12
  mcp.digitalWrite(ttlblock2OE, LOW); //low for enable
  mcp.digitalWrite(ttlblock2DIR, HIGH); //high to enable 3.3v -> 5V output

  //configure TTL outputs 13-16 & TRIG 1-4
  mcp.digitalWrite(ttlblock1OE, LOW); //low for enable
  mcp.digitalWrite(ttlblock1DIR, LOW); //high to enable 3.3v -> 5V output
  delay(10);
  configureTrigger(TRG[0]); //will attach interrupt
  for (byte i = 0; i < 9; ++i) {
    pinMode(ttl[i], OUTPUT);  //SET OUTPUT PINS ON TTL AND CAMERA LINES
    digitalWrite(ttl[i], LOW);
  }
  for (byte i = 9; i < 16; ++i) {
    mcp.pinMode(ttl[i], OUTPUT);
    delay(5);
    mcp.digitalWrite(ttl[i], LOW);
    delay(10);
  } //SET OUTPUT PINS ON TTL AND CAMERA LINES
  mcp.digitalWrite(pwrLed, HIGH); //indicate setup complete

  Serial.begin(115200); // start serial @ 115,200 baud
  //randomSeed(analogRead(A0));
  while (!Serial) { //Waits here until serial port is opened on PC side
    ;  // wait for serial port
  }

  //read from SD card
  /*
    if (loadSet()) {
    Serial.println("SD Settings Loaded");
    }
    else {
    Serial.println("No Settings Loaded from SD, File Missing or No Card Found");
    }
  */
  /***Dac startup ***/
  pinMode(9, OUTPUT); //CLR pin must stay high!
  digitalWrite(9, LOW); //CLR Stays high ALWAYAS
  delay(50);
  digitalWrite(9, HIGH); //CLR Stays high ALWAYAS
  delay(50);

  SPI.begin();
  pinMode(10, OUTPUT); // DAC CS
  SPI.beginTransaction(SPISettings(30000000, MSBFIRST, SPI_MODE0)); //teensy can do 30000000 !!


  for (byte d = 0; d < 16; ++d) {
    //span all DAC lines to set range
    setDACRange(d, initDACRange);
  }

  //Drive All DACs & TTLs to 0
  for (int i = 0; i < 16; ++i) {
    setTTL(i, 0);
    setDACVoltage(i, 0);
  }
  printID(); //issue identifier so software knows we are running

  delay(10);
  mcp.digitalWrite(15, HIGH); //indicate setup complete
  //byte a=0;
  //volatile int f=0;
  //Wire.setClock(400000);

}

void loop()
{

  //************************   DEVICE CONTROL & COMMAND CODE          ***********************//
  //************************  SERIAL COMMUNICATION CODE    ******************///
  if (!Serial) {
    reboot();
  }

  if (stringComplete)  //Check whatever came in on serial
  {
    mcp.digitalWrite(readyLed, LOW);
    if (inputString == "*\n") {
      printID(); //return ID line if queried
    }

    //Message commands
    if (inputString.substring(0, 9) == "PARAMETER")   {
      readParameter(inputString);
    }
    if (inputString == "STAT?\n")                     {
      debug();
    }
    if (inputString == "SAVESETTINGS\n")              {
      if (saveSet()) {
        Serial.println("!SAVESETTINGS");
      }
    }
    if (inputString == "TEST?\n")                     {
      diagTest();
    }
    if (inputString == "CLEAR_ALL\n")                 {
      clearTable();
    }
    if (inputString == "RESET\n")                     {
      reboot();
    }
    if (inputString == "STARTWAVE\n")                 {
      waveFunction();
    }
    if (inputString == "CLEAR_FOCUS\n")               {
      clearFocus();
    }
    if (inputString == "CLEAR_DELAY\n")               {
      clearDelay();
    }
    if (inputString == "SPEED_TEST\n")                {
      speedtest();
    }
    if (inputString.substring(0, 9) == "CLEAR_DAC")    {
      clearDac();
    }
    if (inputString.substring(0, 9) == "CLEAR_TTL")    {
      clearTtl();
    }


    //------------------------------------ SET DAC OUTPUT VOLTAGE ------------------------------------------

    if (inputString.substring(0, 3) == "DAC") {
      uint8_t DACChannel;
      float DACVoltage;
      uint8_t index;
      if (inputString[4] == 44) { //If fifth charachter is comma
        DACChannel = (uint8_t)inputString.substring(3, 4).toInt();  //If less than 10, assign single digit value
        index = 5; //Index of charactera after comma
      }
      else {
        DACChannel = (uint8_t)inputString.substring(3, 5).toInt();  //IF greater than 10, assign both chars to integer
        index = 6; //Index of charactera after comma
      }

      if (DACChannel < 0 || DACChannel > 15) {
        Serial.println("DAC channel is not available");
      }
      else {
        DACVoltage = inputString.substring(index, inputString.length() - 1).toFloat(); //Get float value after comma
        if (VMin[DACChannel] < DACVoltage && DACVoltage < VMax[DACChannel]) {
          setDACVoltage(DACChannel, DACVoltage);
          Serial.print("DAC voltage set to: ");
          Serial.print(DACVoltage);
          Serial.println(" V");
        }
        else {
          Serial.println("DAC Voltage is out of range");
        }
      }
    }


    //------------------------------------ SET TTL OUTPUT ------------------------------------------


    if (inputString.substring(0, 3) == "TTL")
    {
      char dIn[2] = {inputString[3], inputString[4]}; //grab TTL Line #
      byte ttlNum = 0;
      if (dIn[2] == 44) {
        ttlNum = atoi(&dIn[1]);  //IF less than 10, assign single digit value
      }
      else {
        ttlNum = atoi(dIn);  //IF greater than 10, assign both chars to integer
      }

      byte ttlStat = 0;
      if (ttlNum < 10) {
        ttlStat = atoi(&inputString[5]); //snag ttl value if < 10
      }
      else {
        ttlStat = atoi(&inputString[6]); //snag ttl Value if > 10
      }
      //byte ttlNum = atoi(&inputString[3]); //snag ttl line #
      if (ttlStat > 1) {
        ttlStat = 1; //force to boolean range
      }
      boolean goodRange = true;
      if (ttlNum < 0 || ttlNum > 15) {
        goodRange = false; //confirm if input channel range is valid
      }
      if (goodRange) //if range is OK perform command
      {
        Serial.print("!TTL"); //print recieve message to operator
        Serial.print(ttlNum);
        Serial.print(",");
        Serial.println(ttlStat);
        setTTL(ttlNum, ttlStat);
        mcp.digitalWrite(ttlLed, ttlActive > 0);

        clearSerial();
      }
      if (!goodRange) //if range is outside return failure msg to user
      {
        Serial.println("TTL channel out of Range. Valid is 0-15...");
      }
    }


    //------------------------------------ RUN PROG_WAVE FUNCTION  ------------------------------------------
    //This function is now probably obsolete

    //example string to this entry = "PROG_WAVE,1,1,10,0,100,10"
    if (inputString.substring(0, 9) == "PROG_WAVE")
    {
      byte dline = 0; //Dac line to assign for this waveform, only 2x forms may be generated!
      byte tline = 0;
      byte wstep = 0; //number of steps to run befor restarting
      int wtrig = 0;  // wave trigger value = 0= free run, 1= use prog del array # 1, 2 = change of TRIG 1, 3 = rising TRIG1 4 = falling fo trig 1
      byte charPos = 10; //default position and index of the character counter for the string input
      byte stepper = 0; //used for looking at the text and finding the values
      String nums = ""; //character array to hold numbers
      byte freqTTL = 0; //delay time for each loop
      byte freqDAC = 0; //delay time for each loop
      byte cycle = 0;
      byte arrayPos = 0;
      for (byte i = 0; i < 7; ++i) { //loop this function to pull 7 integers from our string,
        while (inputString[charPos] != ',' && inputString[charPos] != '\n' )
        {
          if (isDigit(inputString[charPos])) //make sure it's a real #
          {
            nums += (char)inputString[charPos];
            ++charPos;
          } //search for a comma
          else break;
          if (charPos > 200) {
            break; //in case the user forgot a comma
          }
        }
        //if(i==0) {dline = nums.toInt() ;} //DAC line #
        //if(i==1) {wstep   = nums.toInt() ;} //step value
        //if(i==2) {wtrig   = nums.toInt() ;} //convert the string to an integer value
        if (i == 0) {
          dline = nums.toInt() ; //DAC line #
        }
        if (i == 1) {
          tline = nums.toInt() ; //TTL line #
        }
        if (i == 2) {
          wstep   = nums.toInt() ; //step value
        }
        if (i == 3) {
          wtrig   = nums.toInt() ; //convert the string to an integer value
        }
        if (i == 4) {
          freqDAC = nums.toInt() ; //convert the string to an integer value
        }
        if (i == 5) {
          freqTTL = nums.toInt() ;
        }
        if (i == 6) {
          cycle   = nums.toInt() ;
        }
        ++charPos; //bump up one to move to next char past comma
        nums = ""; //clear string buffer
      }

      //we have collected values, and now will error check and assign
      boolean valid = true;
      if (dline  < 1 || dline  > 16) {
        valid = false; //dac line test
      }
      //if(dline  < 1 || dline  > 16) {valid=false;} //check table assignment
      if (tline  < 1 || tline  > 16) {
        valid = false; //ttl line test
      }
      //if(tline  < 1 || tline  > 16) {valid=false;} //check table assignment
      if (valid)
      {
        byte wArr = 0;
        waveArray[wArr][0] = dline - 1;
        waveArray[wArr][1] = freqDAC;
        waveArray[wArr][2] = tline;
        waveArray[wArr][3] = cycle;
        waveArray[wArr][4] = wstep;
        waveArray[wArr][5] = wtrig;
        waveArray[wArr][6] = freqTTL;
      }
      if (!valid) {
        Serial.println("one or more values out of range...");
      }
      //Report collected values
      else
      {
        char out[200];
        sprintf(out, "!PROG_WAVE,%u,%u,%u,%u,%u,%u\n", dline, tline, wstep, wtrig, freqDAC, freqTTL, cycle);
        Serial.print(out);
        ++pChannel;
      }
      //NEED WAVEFORM COLLECTOR HERE!
      for (int i = 0; i < wstep; ++i) { //collect all wave values
        String DACst = "";
        String TTLst = "";
        char inChar = 'A';
        while (inChar != ',') {
          while (!Serial.available()) {} //wait for serial data
          inChar = (char)Serial.read();  // get the new byte:
          DACst += inChar; // add it to the inputString:
        }
        //place value in array here
        wArray[i] =  DACst.toInt(); //no error checking yet TODO
        while (inChar != '\n') {
          while (!Serial.available()) {} //wait for serial data
          inChar = (char)Serial.read();  // get the new byte:
          TTLst += inChar; // add it to the inputString:
        }
        //place value in array here
        tArray[i] =  TTLst.toInt(); //no error checking yet TODO
      }

      for (int i = 0; i < wstep; ++i) { //repot all wave values
        char out[200];
        sprintf(out, "!%u,DAC,%u,TTL,%u\n", i, wArray[i], tArray[i]);
        Serial.print(out);
      }
    }


    //------------------------------------ RUN RASTER_SCAN ------------------------------------------

    if (inputString.substring(0, 11) == "RASTER_SCAN")//Remove .substring
    {
      String TSStatus = "Running raster scan";
      Serial.println(TSStatus);

      float dimOnePosV = 0;
      float dimTwoPosV = 0;
      float dimThreePosV = 0;
      float dimFourPosV = 0;

      float dimOnePrimeV;
      float dimTwoPrimeV;

      mcp.digitalWrite(dacLed, 1); //turn on DAC LED

      while (abs(dimFourPosV) <= abs(dimFourLenV)) {
        setDACVoltage(dimFourChan, dimFourStartV + dimFourPosV);
        while (abs(dimThreePosV) <= abs(dimThreeLenV)) {
          setDACVoltage(dimThreeChan, dimThreeStartV + dimThreePosV);
          while (abs(dimTwoPosV) <= abs(dimTwoLenV)) {
            while (abs(dimOnePosV) <= abs(dimOneLenV)) {
              if (dimOneStepSizeV == 0) {
                break;
              }
              dimOnePrimeV = dimOnePosV * cos(angleRad) - dimTwoPosV * sin(angleRad);
              dimTwoPrimeV = dimOnePosV * sin(angleRad) + dimTwoPosV * cos(angleRad);
              setDACVoltage(dimOneChan, dimOneStartV + dimOnePrimeV);
              setDACVoltage(dimTwoChan, dimTwoStartV + dimTwoPrimeV);
              //Pixel cycle
              runPixelCycle();
              //--------
              dimOnePosV += dimOneStepSizeV;
            }
            dimOnePosV = 0;
            if (dimTwoStepSizeV == 0) {
              break;
            }
            dimTwoPosV += dimTwoStepSizeV;
          }
          dimTwoPosV = 0;
          if (dimThreeStepSizeV == 0) {
            break;
          }
          dimThreePosV += dimThreeStepSizeV;
        }
        dimThreePosV = 0;
        if (dimFourStepSizeV == 0) {
          break;
        }
        dimFourPosV += dimFourStepSizeV;
      }
      setDACVoltage(dimOneChan, dimOneStartV);
      setDACVoltage(dimTwoChan, dimTwoStartV);
      setDACVoltage(dimThreeChan, dimThreeStartV);
      setDACVoltage(dimFourChan, dimFourStartV);

      mcp.digitalWrite(dacLed, 0); //turn off DAC LED
      Serial.println("Scan done");
    }

    //------------------------------------ RUN pLS-RESOLFT_SCAN ------------------------------------------

    if (inputString.substring(0, 16) == "pLS-RESOLFT_SCAN")//Remove .substring
    {
      String TSStatus = "Running pLS-RESOLFT_SCAN scan";
      Serial.println(TSStatus);
      mcp.digitalWrite(dacLed, 1);

      float cycleBaseLineV;
      //Insert cycle loop HERE
      for(int tp = 0; tp < timeLapsePoints; tp++)
      {
        for (int k = 0; k < cycleSteps; k++)
        {
          cycleBaseLineV = cycleStartV + k*cycleStepSizeV;
          //setDACVoltage(cycleScanDACChan, cycleStartV + k*cycleStepSizeV); //Place stage in correct position
          setDACVoltage(roScanDACChan, cycleBaseLineV + roRestingV); //Place galvo in resting position (where it should be when on/off pulses are pulsed)
          //Wait to allow for read out of previous frame if not the first cycle
          if (k != 0)
          {
            sincepLSRevent = 0;
            waitUntil(sincepLSRevent, delayBeforeOnUs);
          }
          //Turn on on-laser
          setTTL(onLaserTTLChan, 1);
          sincepLSRevent = 0;
          //Turn off on-laser
          waitUntil(sincepLSRevent, onPulseTimeUs);
          setTTL(onLaserTTLChan, 0);
          sincepLSRevent = 0;
          //Turn on off-laser
          waitUntil(sincepLSRevent, delayAfterOnUs);
          setTTL(offLaserTTLChan, 1);
          sincepLSRevent = 0;
          //Turn off off-laser
          waitUntil(sincepLSRevent, offPulseTimeUs);
          setTTL(offLaserTTLChan, 0);
          sincepLSRevent = 0;
          //Start read-out scan
          waitUntil(sincepLSRevent, delayAfterOffUs);
          for (int i = 0; i < roSteps; i++)
          {
            setDACVoltage(roScanDACChan, cycleBaseLineV + roStartV + i * roStepSizeV);
            sincepLSRevent = 0;
            //Turn on ro-laser
            waitUntil(sincepLSRevent, delayAfterDACStepUs);
            setTTL(roLaserTTLChan, 1);
            sincepLSRevent = 0;
            //Turn off ro-laser
            waitUntil(sincepLSRevent, roPulseTimeUs);
            setTTL(roLaserTTLChan, 0);
            sincepLSRevent = 0;
            //Wait after RO pulse
            waitUntil(sincepLSRevent, delayAfterRoUs);
          }
        }
        String msg = "Timepoint " + (String)tp + " done";
        Serial.println(msg);
        //Wait for the timelapse delay if not the last timepoint
        if (tp < (timeLapsePoints - 1))
        {
          sincepLSRevent = 0;
          waitUntil(sincepLSRevent, timeLapseDelayUs);
        }
        Serial.println("MSG0001");
      }
      //Reset voltages
      //setDACVoltage(cycleScanDACChan, cycleStartV);
      setDACVoltage(roScanDACChan, roRestingV);
      mcp.digitalWrite(dacLed, 0); //turn off DAC LED
      Serial.println("Scan done");
    }
    clearSerial();
    mcp.digitalWrite(readyLed, HIGH);
  } //EXIT LOOP FOR SERIAL HERE

} //close main loop



void runPixelCycle() {
  sincePixelCycleStart = 0;
  waitUntil(sincePixelCycleStart, p1StartUs);
  //Temporary fix
  setTTL(0, 1);
  setTTL(1, 1);
  setTTL(2, 1);
  setTTL(3, 1);
  waitUntil(sincePixelCycleStart, p1EndUs);
  setTTL(0, 0);
  setTTL(1, 0);
  setTTL(2, 0);
  setTTL(3, 0);
  //---
  /*
    setTTL(p1Line, 0);
    waitUntil(sincePixelCycleStart, p2StartUs);
    setTTL(p2Line, 1);
    waitUntil(sincePixelCycleStart, p2EndUs);
    setTTL(p2Line, 0);
    waitUntil(sincePixelCycleStart, p3StartUs);
    setTTL(p3Line, 1);
    waitUntil(sincePixelCycleStart, p3EndUs);
    setTTL(p3Line, 0);
  */
  waitUntil(sincePixelCycleStart, sequenceTimeUs);
}

void waitUntil(elapsedMicros counter, uint32_t timeout) {
  while (counter < timeout) {
    ;
  }
}

void waveFunction() { // waveArray [wave 1/2] [0:DAC, 1:Form (sine,saw,triangle,square),2: center, 3:amplitude, 4:step per cycle, 5: duty (if used), 6: phase, 7: trigger type ),
  for (int n = 0; n < waveArray[0][3]; n++) { //continuous operation until serial event recieved
    for (int i = 0; i < waveArray[0][4]; i++) { //loop through # of steps
      setDACValue(waveArray[0][0], wArray[i]); // Set DAC Lines
      delay((waveArray[0][1] - waveArray[0][6]) / 2);
      setTTL(waveArray[0][2], wArray[i]); //set ttl value 1
      delay(waveArray[0][6]);
      setTTL(waveArray[0][2], 0); //set ttl value 0
      delay((waveArray[0][1] - waveArray[0][6]) / 2);
    }
  }
}

byte loadSet() {
  if (!SD.begin(chipSelect)) {
    Serial.println("SD Access failure, contact ARC");
    return;
  }
  myFile = SD.open("DAC.txt");
  if (myFile) {
    byte d = 0;
    byte n = 0;
    while (myFile.available() && n < 17) {
      d = myFile.read();
      d = d - 48;
      //byte dline = inputString.substring(5).toInt();
      //Serial.println(d);
      RNG[n] = d; //assign read value to active range array
      n++;
    }
    myFile.close();

  } else {
    return 0;
  }

  myFile = SD.open("TRG.txt");
  if (myFile) {
    byte d = 0;
    byte n = 0;
    while (myFile.available()) {
      d = myFile.read();
      d = d - 48;
      //Serial.print("TRIG = ");
      //Serial.println(d);
      TRG[n] = d; //assign the trigger flag to the array
      n++;
    }
    myFile.close();
    return 1;
  } else {
    return 0;
  }
}


void reboot() { //resets the board
  mcp.digitalWrite(15, LOW);
  delay(100);
  Serial.println("Running reboot\n");
  setup();
}

byte saveSet() {
  if (!SD.begin(chipSelect)) {
    Serial.println("SD Access failure, contact ARC");
    return;
  }

  // open the file.
  myFile = SD.open("DAC.txt", O_WRITE | O_CREAT | O_TRUNC);
  if (myFile) { //assuming it opened properly...
    for (byte f = 0; f < 16; ++f) {
      myFile.print(RNG[f]);  //save in all active dac range values
    }
    myFile.close();
  }
  else {
    return 0;
  }

  myFile = SD.open("TRG.txt", O_WRITE | O_CREAT | O_TRUNC);
  if (myFile) { //assuming it opened properly...
    for (byte f = 0; f < 4; ++f) {
      myFile.print(TRG[f]);
    }
    myFile.close();
    return 1;
  }
  else {
    return 0;
  }
}

void clearSerial() {
  //STUFF TO CLEAN OUT THE SERIAL LINE
  inputString = "";     // clear the string:
  stringComplete = false;
}

/*Set DAC Value*/
void setDACValue(byte DACChan, int int16Value) {
  dac_write(10, 0, DACChan, int16Value); // Send dac_code
  currentDACValues[DACChan] = int16Value; //Save value set
}

void setDACVoltage(byte DACChan, float voltage) {
  int int16Value = (int)(65535.0 * (voltage - VMin[DACChan]) / (VMax[DACChan] - VMin[DACChan]));
  setDACValue(DACChan, int16Value);
}

/*SET TTL CONTROL*/
void setTTL(byte t1, boolean t2) {
  //NOTE: t1 is not assumed to be given as zero-indexed channel value.
  bitWrite(ttlActive, t1, t2); //assign ttlActive new output value
  if (t1 < 9) {
    digitalWriteFast(ttl[t1], t2); //case where the write operation is using existing uController pins
  }
  //This part comes from the original Triggerscope firmware, but is a bit unclear...
  else if (t1 > 8) {

    //mcp.digitalWrite(ttl[t1],t2);
    uint8_t mask = highByte(ttlActive); //mask covers GPIOA of TTL values
    mask = mask >> 1; //shift left to provide room for last bit, should be a zero as this is the ttl13-16 output

    if ( (t1 > 11) && t2) {
      bitWrite(mask, 7, 1); //if output is on last shifter && positive set register as output
      mcp.writeGPIO(mask, 0);
      bitWrite(mask, 7, 0);
      mcp.writeGPIO(mask, 0); //write all off for GPIOA use hex 0x80 for LS2 direction OUTPUT
    }

    else if ( (t1 > 11) && !t2) {
      bitWrite(mask, 7, 1); //if output is on last shifter && positive set register as output
      mcp.writeGPIO(mask, 0);
      bitWrite(mask, 7, 0);
      mcp.writeGPIO(mask, 0); //write all off for GPIOA use hex 0x80 for LS2 direction OUTPUT
    }
    else if (t1 < 12) { // TTL 8-12 send a simple update
      //bitWrite(mask,7,0);
      bitWrite(mask, 7, 0);
      mcp.writeGPIO(mask, 0); //write all off for GPIOA use hex 0x80 for LS2 direction OUTPUT
    }

  }

}
/*SERIAL COMMO*/
void serialEvent() {
  trigArmed = false;
  while (Serial.available()) {
    // get the new byte:
    char inChar = (char)Serial.read();
    // add it to the inputString:
    inputString += inChar;
    // if the incoming character is a newline, set a flag
    // so the main loop can do something about it:
    if (inChar == '\n') {
      stringComplete = true;
    }
  }
}

/*INTERRUPT CODE FOR TTL INPUT ***************/
void sigIn()     //sigin is the input response line - this recieves the trigger input from an external source
{
  //Serial.write("T");
  inTrigger = true;
  if (digitalRead(trig[0]) ) {
    tState = true; //Martyn Addition
  }
  else if (!digitalRead(trig[0])) {
    tState = false; //Martyn Addition
  }
}

void configureTrigger(byte tOption) {
  TRG[0] = tOption; //assign input value to global
  switch (TRG[0]) {
    case 0:
      //attachInterrupt(digitalPinToInterrupt(trig[0]),sigIn,LOW);
      //deprecated for teensy
      break;
    case 1:
      //attachInterrupt(digitalPinToInterrupt(trig[0]),sigIn,HIGH);
      //depricated on teensy
      break;
    case 2:
      attachInterrupt(digitalPinToInterrupt(trig[0]), sigIn, RISING);
      break;
    case 3:
      attachInterrupt(digitalPinToInterrupt(trig[0]), sigIn, FALLING);
      break;
    case 4:
      attachInterrupt(digitalPinToInterrupt(trig[0]), sigIn, CHANGE);
      break;
  }
}

void debug()
{
  if (debugT < millis() ) //if this is the first time debug has run, this will execute, otherwise has enough time elapsed?
  {
    Serial.print("TTL STATES:");
    //REPORT TTL
    for (int i = 0; i < 16; ++i)
    {
      char sOut[100];
      sprintf(sOut, "%d=%d,", i + 1, digitalRead(ttl[i]));
      Serial.print(sOut);
    }
    Serial.println("");
    Serial.print("TTL Pins ( 9+ = MCU # ):");
    for (int i = 0; i < 16; ++i)
    {
      char sOut[100];
      sprintf(sOut, "%d=%d,", i + 1, ttl[i]);
      Serial.print(sOut);
    }
    Serial.println("");
    //REPORT DAC
    Serial.print("DAC:");
    for (int i = 0; i < 16; ++i)
    {
      char sOut[200];
      sprintf(sOut, "%d=%u,", i + 1, currentDACValues[i]);
      Serial.print(sOut); //used to print sOut
    }
    Serial.println();
    Serial.print("DAC Ranges: ");
    for (int i = 0; i < 16; ++i) {
      Serial.print(RNG[i]) ; //range saves
      Serial.print(", ");
    }
    Serial.println();
    Serial.print("TRIG Settings: ");
    Serial.print(TRG[0]); Serial.print(", ");
    Serial.print(TRG[1]); Serial.print(", ");
    Serial.print(TRG[2]); Serial.print(", ");
    Serial.print(TRG[3]); Serial.println();


    Serial.print("Focus Position = ");
    Serial.print(currentDACValues[focus]); //focus is ALWAYS on line 15!
    Serial.println("");
    char sOut[255];
    //start,step,loop,direction,slave
    sprintf(sOut, "FOCUS ARRAY = Start: %u Step: %u Loop: %u Direction: %u Slave: %u Current Step: %u\n",
            focArray[0], focArray[1], focArray[2], focArray[3], focArray[4], focArray[5]);
    Serial.print(sOut);

    Serial.print("Focus DAC Line = ");
    Serial.println(DAC[15] + 1);

    //Report program arrays
    Serial.println("***Sequencer Programming Status***");
    Serial.print("MaxProgram = ");
    Serial.println(maxProgram);
    //report DACs
    Serial.println("PROG, DAC1, DAC2, DAC3, DAC4, DAC5, DAC6, DAC7, DAC8, DAC9,DAC10,DAC11,DAC12,DAC13,DAC14,DAC15,DAC16/FOCUS");
    for (int p = 0; p < maxProgram + 1; ++p) //list all recorded programs
    {
      char sOut[200];
      sprintf(sOut, "P:%2d,", p + 1);
      Serial.print(sOut);
      for (byte nVal = 0; nVal < 16; ++nVal)
      {
        sprintf(sOut, "%05u,", dacArray[p][nVal]);
        Serial.print(sOut);
      }
      Serial.println("");
    }

    //Report TTL's
    Serial.println("PROG, TTL1, TTL2, TTL3, TTL4, TTL5, TTL6, TTL7, TTL8, TTL9,TTL10,TTL11,TTL12,TTL13,TTL14,TTL15,TTL16");
    for (int p = 0; p < maxProgram + 1; ++p) //list all recorded programs
    {
      char sOut[200];
      sprintf(sOut, "P:%2d,", p + 1);
      Serial.print(sOut);
      for (byte nVal = 0; nVal < 16; ++nVal)
      {
        sprintf(sOut, "    %d,", ttlArray[p][nVal]);
        Serial.print(sOut);
      }
      Serial.println("");
    }

    debugT = millis() + 500; // wait 500ms before the next report
  }
}

void diagTest()
{

}

void printID()
{
  Serial.println(idname);
}

void clearTable()
{
  for (byte i = 0; i < 16; ++i) //all 16 channels
  {
    for (byte n = 0; n < 50; ++n) //all program lines
    {
      dacArray[n][i] = 0; //clear dac
      ttlArray[n][i] = 0; //clear ttl
      delArray[n]    = 0; //clear delay
    }
  }
  clearFocus();  //clear focus
  maxProgram = 0; //reset program max
  digitalWrite(9, LOW); //CLR Stays high ALWAYAS
  delay(10);
  digitalWrite(9, HIGH); //CLR Stays high ALWAYAS

  Serial.println("!CLEAR_ALL");
}

void clearDac()
{
  byte offSet = 10;
  char instring[15] = {}; //create a string to hold char ascii for later conversion to integer value
  for (byte sl = 0; sl < inputString.length() - offSet; ++sl)
  { //figure out length of string and calc # characters which (should be) numbers for DAC
    instring[sl] = inputString[sl + offSet]; //assign 7th and farther numbers to char table
    //Serial.print(fstring[sl]);
  }
  byte inLine = atoi(instring); //convert char table to useable integer for DAC level
  inLine = inLine - 1;
  for (byte i = 0 ; i < 50; ++i)
  {
    dacArray[i][inLine] = 0;
  }
  Serial.print("!CLEAR_DAC,"); //print recieve message to operator
  Serial.println(inLine + 1);
}

void clearTtl()
{
  byte offSet = 10;
  char instring[15] = {}; //create a string to hold char ascii for later conversion to integer value
  for (byte sl = 0; sl < inputString.length() - offSet; ++sl)
  { //figure out length of string and calc # characters which (should be) numbers for DAC
    instring[sl] = inputString[sl + offSet]; //assign 7th and farther numbers to char table
    //Serial.print(fstring[sl]);
  }
  byte inLine = atoi(instring); //convert char table to useable integer for DAC level
  inLine = inLine - 1;
  for (byte i = 0 ; i < 50; ++i)
  {
    ttlArray[i][inLine] = 0;
  }
  Serial.print("!CLEAR_TTL,"); //print recieve message to operator
  Serial.println(inLine + 1);
}

void clearDelay()
{
  for (byte i = 0 ; i < 50; ++i)
  {
    delArray[i] = 0;
  }
  Serial.println("!CLEAR_DELAY"); //print recieve message to operator

}

void clearFocus()
{
  for (byte i = 0 ; i < 6; ++i)
  {
    focArray[i] = 0;
  }
  Serial.println("!CLEAR_FOCUS"); //print recieve message to operator
}

void setDACRange(byte dacLine, byte range)
{
  /*dacLine 0 indexed
     range 0-5 corresponds to the following:
      SPAN_0_TO_5V             0x0000
      SPAN_0_TO_10V            0x0001
      SPAN_PLUS_MINUS_5V       0x0002
      SPAN_PLUS_MINUS_10V      0x0003
      SPAN_PLUS_MINUS_2V5      0x0004
  */
  dac_write(10, 1, dacLine, range); //issue span command
  dac_write(10, 2, 0, 0); //issue update all lines command
  RNG[dacLine] = range;
  if (range == 0) {
    VMin[dacLine] = 0;
    VMax[dacLine] = 5;
  }
  if (range == 1) {
    VMin[dacLine] = 0;
    VMax[dacLine] = 10;
  }
  if (range == 2) {
    VMin[dacLine] = -5;
    VMax[dacLine] = 5;
  }
  if (range == 3) {
    VMin[dacLine] = -10;
    VMax[dacLine] = 10;
  }
  if (range == 4) {
    VMin[dacLine] = -2.5;
    VMax[dacLine] = 2.5;
  }
}


void spanTest()
{

}


void speedtest() {
  Serial.println("Starting Speed Test...");
  clearSerial();

  for ( byte n = 0; n < 10; ++n) {
    setTTL(15, 1);
    //delay(1);
    setTTL(15, 0);
    //delay(0);
    //delayMicroseconds(10);
  }


  /*
    while(Serial.available() == 0) {
    for(volatile int f=10000;f<40001;f=f+5000){
        while(!inTrigger){}//wait...
        dac_write(10,0, 0, f); // Set DAC Lines
        dac_write(10,0, 1, 40000-f); // Set DAC Lines
        inTrigger=false;
      }
    }

  */
}

int8_t dac_write(uint8_t cs, byte command, uint8_t dac_address, uint16_t dac_code) {
  // Write the 16-bit dac_code
  /*
    Serial.print(" DW=");
    Serial.print( dac_address);
    Serial.print(",");
    Serial.println(dac_code);
  */
  static uint8_t last_data_array[4];
  uint8_t data_array[4], rx_array[4];
  int8_t ret;
  LT_union_int16_2bytes data;

  data.LT_int16 = dac_code;                              // Copy DAC code
  data_array[3] = 0;                                     // Only required for 32 byte readback transaction
  if (command == 0) {
    data_array[2] = 0x30 | dac_address; // Build command / address byte
  }
  if (command == 1) {
    data_array[2] = 0x60 | dac_address; // span dac
  }
  if (command == 2) {
    data_array[2] = 0xA0 | dac_address;
  }
  // ***NOT SURE WHY BUT THIS MUST BE OFF! data_array[2] = 0x30 | dac_address;             // Build command / address byte
  data_array[1] = data.LT_byte[1];                       // MS Byte
  data_array[0] = data.LT_byte[0];                       // LS Byte
  /*
    #define  LTC2668_CMD_WRITE_N              0x00  //!< Write to input register n
    #define  LTC2668_CMD_UPDATE_N             0x10  //!< Update (power up) DAC register n
    #define  LTC2668_CMD_WRITE_N_UPDATE_ALL   0x20  //!< Write to input register n, update (power-up) all
    #define  LTC2668_CMD_WRITE_N_UPDATE_N     0x30  //!< Write to input register n, update (power-up)
    #define  LTC2668_CMD_POWER_DOWN_N         0x40  //!< Power down n
    #define  LTC2668_CMD_POWER_DOWN_ALL       0x50  //!< Power down chip (all DAC's, MUX and reference)
    #define  LTC2668_CMD_SPAN                 0x60  //!< Write span to dac n
    #define  LTC2668_CMD_CONFIG               0x70  //!< Configure reference / toggle
    #define  LTC2668_CMD_WRITE_ALL            0x80  //!< Write to all input registers
    #define  LTC2668_CMD_UPDATE_ALL           0x90  //!< Update all DACs
    #define  LTC2668_CMD_WRITE_ALL_UPDATE_ALL 0xA0  //!< Write to all input reg, update all DACs
    #define  LTC2668_CMD_MUX                  0xB0  //!< Select MUX channel (controlled by 5 LSbs in data word)
    #define  LTC2668_CMD_TOGGLE_SEL           0xC0  //!< Select which DACs can be toggled (via toggle pin or global toggle bit)
    #define  LTC2668_CMD_GLOBAL_TOGGLE        0xD0  //!< Software toggle control via global toggle bit
    #define  LTC2668_CMD_SPAN_ALL             0xE0  //!< Set span for all DACs
    #define  LTC2668_CMD_NO_OPERATION         0xF0  //!< No operation
  */


  spi_transfer_block(cs, data_array, rx_array, (uint8_t) 4);
  // Compare data read back to data that was sent the previous time this function was called
  if ((rx_array[2] == last_data_array[2]) && (rx_array[1] == last_data_array[1]) && (rx_array[0] == last_data_array[0]))
  {
    ret = 0;
  }
  else
  {
    ret = 1;
  }

  last_data_array[0] = data_array[0]; // Copy data array to a static array to compare
  last_data_array[1] = data_array[1]; // the next time the function is called
  last_data_array[2] = data_array[2];

  return (ret);
}

void spi_transfer_block(uint8_t cs_pin, uint8_t *tx, uint8_t *rx, uint8_t length)
{
  int8_t i;
  output_low(cs_pin);                 //! 1) Pull CS low

  for (i = (length - 1);  i >= 0; i--)
    rx[i] = SPI.transfer(tx[i]);    //! 2) Read and send byte array

  output_high(cs_pin);                //! 3) Pull CS high
}




/*******************LICENSING INFO**************

   Copyright (c) 2018, Advanced Research Consulting

   THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS ''AS IS'' AND ANY
   EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
   WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
   DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER BE LIABLE FOR ANY
   DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
   (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
   LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
   ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
   (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
   SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.



 *******************/
