/*
ADS1299 Library for ESP32-S3
Originally created by: Conor Russomanno (https://github.com/conorrussomanno/ADS1299)
Modified by: Xavier Asghar
Modifications include:
 - Replaces ATmega328P SPI implementation with Arduino's built-in SPI library
 - Changes updateData function to be called from an ISR rather than polled from the main loop
 - updateData now returns a integer long rather than printing to the serial monitor
 - Adds updateDataPacket function that drops data directly into a numbered byte array to be sent over bluetooth
*/

# include "ADS1299.h"

SPISettings adsSPI(2000000, MSBFIRST, SPI_MODE1);

void ADS1299::setup(int _DRDY_PIN, int _CS_PIN, int _SCK_PIN, int _MISO_PIN, int _MOSI_PIN, int _RESET_PIN, int _START_PIN){
    
    tCLK = 0.489;   // (uS) Assuming default 2.048 MHz clock
    tSDECODE = 5.0; // (uS) tSDECODE > 4 tCLK (Datasheet, pg. 40)
    scaleFactorUV = 45.0 / (24.0 * 8388608.0);
    outputCount = 0;

    // Initalise pins variablkes
    DRDY_PIN = _DRDY_PIN;
    CS_PIN = _CS_PIN;
    SCK_PIN = _SCK_PIN;
    MISO_PIN = _MISO_PIN;
    MOSI_PIN = _MOSI_PIN;
    RESET_PIN = _RESET_PIN;
    START_PIN = _START_PIN;

    // Initialise pin modes
    pinMode(DRDY_PIN, INPUT);
    pinMode(START_PIN, OUTPUT);
    pinMode(CS_PIN, OUTPUT);
    pinMode(RESET_PIN, OUTPUT);

    digitalWrite(RESET_PIN, HIGH);  // Keep ADS1299 out of reset
    digitalWrite(START_PIN, HIGH);  
    digitalWrite(CS_PIN, HIGH);     // Deselect the ADS1299 initially

    // Initialise SPI
    SPI.begin(SCK_PIN, MISO_PIN, MOSI_PIN, -1);

    delay(1000);                   // tPOR > 0.128s (Datasheet, pg. 70)
    digitalWrite(RESET_PIN, LOW);  
    delayMicroseconds(2);          // tRST > 0.977us (Datasheet, pg. 70)
    digitalWrite(RESET_PIN, HIGH); 
    delay(10);                     // Wait > 18 tCLK (Datasheet, pg. 70)
    
}

//System Commands
void ADS1299::WAKEUP() {
    SPI.beginTransaction(adsSPI);
    digitalWrite(CS_PIN, LOW);      // Set CS Low to communicate
    delayMicroseconds(tSDECODE);
    SPI.transfer(_WAKEUP);
    delayMicroseconds(tSDECODE);    // Must wait 4 or more tCLK cycles before taking CS high (Datasheet, pg. 38)
    digitalWrite(CS_PIN, HIGH);     // Set CS High to end communication
    SPI.endTransaction();
    delayMicroseconds(tSDECODE);        
}

void ADS1299::STANDBY() {
    SPI.beginTransaction(adsSPI);
    digitalWrite(CS_PIN, LOW);      
    delayMicroseconds(tSDECODE);
    SPI.transfer(_STANDBY);
    delayMicroseconds(tSDECODE);    
    digitalWrite(CS_PIN, HIGH);  
    SPI.endTransaction();   
    delayMicroseconds(tSDECODE);     
}

void ADS1299::RESET() {
    SPI.beginTransaction(adsSPI);
    digitalWrite(CS_PIN, LOW);      
    delayMicroseconds(tSDECODE);
    SPI.transfer(_RESET);
    delayMicroseconds(tSDECODE);    
    digitalWrite(CS_PIN, HIGH); 
    SPI.endTransaction();    
    delayMicroseconds(10);          // At least 18 tCLK cycles required to execute RESET commmand (Datasheet, pg. 41) 
}

void ADS1299::START() {
    SPI.beginTransaction(adsSPI);
    digitalWrite(CS_PIN, LOW);      
    delayMicroseconds(tSDECODE);
    SPI.transfer(_START);
    delayMicroseconds(tSDECODE);    
    digitalWrite(CS_PIN, HIGH);
    SPI.endTransaction();     
    delayMicroseconds(tSDECODE);   
}

void ADS1299::STOP() {
    SPI.beginTransaction(adsSPI);
    digitalWrite(CS_PIN, LOW);      
    delayMicroseconds(tSDECODE);
    SPI.transfer(_STOP);
    delayMicroseconds(tSDECODE);    
    digitalWrite(CS_PIN, HIGH); 
    SPI.endTransaction();    
    delayMicroseconds(tSDECODE);   
}

//Data Read Commands
void ADS1299::RDATAC() {
    SPI.beginTransaction(adsSPI);
    digitalWrite(CS_PIN, LOW);      
    delayMicroseconds(tSDECODE);
    SPI.transfer(_RDATAC);
    delayMicroseconds(tSDECODE);    
    digitalWrite(CS_PIN, HIGH);  
    SPI.endTransaction();   
    delayMicroseconds(tSDECODE);   
}

void ADS1299::SDATAC() {
    SPI.beginTransaction(adsSPI);
    digitalWrite(CS_PIN, LOW);      
    delayMicroseconds(tSDECODE);
    SPI.transfer(_SDATAC);
    delayMicroseconds(tSDECODE);    
    digitalWrite(CS_PIN, HIGH);   
    SPI.endTransaction();  
    delayMicroseconds(tSDECODE);  
}

void ADS1299::RDATA() {
    SPI.beginTransaction(adsSPI);
    digitalWrite(CS_PIN, LOW);      
    delayMicroseconds(tSDECODE);
    SPI.transfer(_RDATA);
    delayMicroseconds(tSDECODE);    
    digitalWrite(CS_PIN, HIGH);    
    SPI.endTransaction(); 
    delayMicroseconds(tSDECODE);  
}

uint8_t ADS1299::RREG(byte _address) {
    SPI.beginTransaction(adsSPI);
    digitalWrite(CS_PIN, LOW);
    delayMicroseconds(tSDECODE);

    // Byte 1: 001r rrrr, where r rrrr is the starting register address.
    SPI.transfer(_RREG | _address);
    delayMicroseconds(tSDECODE); 

    // Byte 2: 00n nnnn, where n nnnn is the number of registers to read – 1
    SPI.transfer(0x00);
    delayMicroseconds(tSDECODE); 

    // Byte 3: Send dummy byte (0x00) to keep SPI clock running.
    uint8_t regValue = SPI.transfer(0x00);
    delayMicroseconds(tSDECODE);

    digitalWrite(CS_PIN, HIGH);
    SPI.endTransaction();
    delayMicroseconds(tSDECODE);  

    // Print the result to the Serial Monitor
    Serial.print("Register Value: 0b");
    for (int i = 7; i >= 0; i--) {
      Serial.print(bitRead(regValue, i)); // Read and print each bit from left to right
    }
    Serial.println("\n");

    return regValue;
}

void ADS1299::WREG(byte _address, byte _value) {
    SPI.beginTransaction(adsSPI);
    digitalWrite(CS_PIN, LOW);
    delayMicroseconds(tSDECODE);

    // Byte 1: 010r rrrr, where r rrrr is the starting register address.
    SPI.transfer(_WREG | _address);
    delayMicroseconds(tSDECODE); 

    // Byte 2: 000n nnnn, where n nnnn is the number of registers to write – 1.
    SPI.transfer(0x00);
    delayMicroseconds(tSDECODE); 

    // Byte 3: Register data (in MSB-first format)
    SPI.transfer(_value);
    delayMicroseconds(tSDECODE);

    digitalWrite(CS_PIN, HIGH);
    SPI.endTransaction();
    delayMicroseconds(tSDECODE);  

    // Print confirmation to Serial Monitor
    Serial.print("Register 0x");
    Serial.print(_address, HEX);
    Serial.println(" modified. \n");
}

void ADS1299::updateData(){
// This function assumes that DRDY is LOW and that the ADS1299 is in continuous data mode (RDATAC)
    SPI.beginTransaction(adsSPI);
    digitalWrite(CS_PIN, LOW);
    delayMicroseconds(tSDECODE);

    long output[9];
    long dataPacket;
    for(int i = 0; i<9; i++){
        dataPacket = 0;
        for(int j = 0; j<3; j++){
            byte dataByte = SPI.transfer(0x00);
            dataPacket = (dataPacket<<8) | dataByte;
        }

        // Sign extend the 24-bit data to 32 bits
        if (dataPacket & 0x00800000) {
            dataPacket |= 0xFF000000;
        }

        output[i] = dataPacket;
    }

    delayMicroseconds(tSDECODE);
    digitalWrite(CS_PIN, HIGH);
    SPI.endTransaction(); 
    delayMicroseconds(tSDECODE);  

    // Serial.println(output[1] * scaleFactorUV, DEC);
}

void ADS1299::updateDataPacket(uint8_t *dataPacket){
// This function assumes that DRDY is LOW and that the ADS1299 is in continuous data mode (RDATAC)
    SPI.beginTransaction(adsSPI);
    digitalWrite(CS_PIN, LOW);
    delayMicroseconds(tSDECODE);

    // Read all 27 bytes (3 status + 24 channel)
    for(int i = 1; i <= 27; i++){ 
        dataPacket[i] = SPI.transfer(0x00);
    }

    delayMicroseconds(tSDECODE);
    digitalWrite(CS_PIN, HIGH);
    SPI.endTransaction(); 
    delayMicroseconds(tSDECODE);  
}





