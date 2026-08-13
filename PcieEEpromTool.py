#! /usr/bin/python

'''
Author: oyang.sun@nettrix.com.cn
Date: 2022-03-03 19:32:51
LastEditTime: 2021-09-02 15:20:29
LastEditors: Please set LastEditors
Description:
FilePath: /code/PcieEEpromTool/PcieEEpromTool.py
'''
import sys,os,time,subprocess
import math
import json
import zlib
import operator


IPMI_CMD_FRU_WRITE_MAX_LEN=64
IPMI_CMD_RAW_HEAD=" raw 0x6 0x52 0x03 0xa8"
IPMI_CMD_MCINFO_CMD=" mc selftest"

IPMI_CMD_HEADER="ipmitool"

EEPROM_OFFSET=32256   ##0x7E00,Bios need to read from here   

HEADER_DATA_LEN=32
HEADER_DATA_CRC0_OFFSET=12
HEADER_DATA_CRC1_OFFSET=13
HEADER_DATA_CRC2_OFFSET=14
HEADER_DATA_CRC3_OFFSET=15

HEADER_DATA_LEN0_OFFSET=6
HEADER_DATA_LEN1_OFFSET=7
ARGS_SIGNATURE=""

def Nettrix_getstatusoutput(cmd):
    if(sys.version[0] == '3'):
        import subprocess  as com
    else:
        import commands as com
    return com.getstatusoutput(cmd)

def CheckUp_parameters(args,cmd):
    global ARGS_SIGNATURE
    if args.ip:
        cmd=cmd + " -H " + args.ip
    if args.username:
        cmd=cmd + " -U " + args.username
    if args.password:
        cmd=cmd + " -P \'" + args.password +"\'"
    if args.interface:
        cmd=cmd + " -I " + args.interface
    if args.write:
        # print args.write
        if not os.path.exists(args.write): 
            print((str(args.write)+" not exist,please check!!!"))
            sys.exit(1)
    elif args.check or args.read:
        pass
    else:
        print("Please input '-h' for help.")
        print("Error: too few arguments!!!")
        sys.exit(1)
    if args.signature:
        ARGS_SIGNATURE=args.signature

    return cmd

def read_Json_file(fileName):
    """
    Get the data for the total json file.
    :param url: <str> json file path.
    :return:  json object data.
    """
    with open(fileName, "r") as json_file:
        try:
            #print cmdResJson
            data = json.load(json_file)
        except Exception as e:
            json_file.close()
            print(("\nError: "+fileName+' not in json format or format error!!!'))
            print(('Please check '+ fileName+' and try again.\n'))
            sys.exit(1)
    json_file.close()
    return data

def read_Bin_file(fileName):
    """
    Get the data for the total bin file.
    :param url: <str> bin file path.
    :return:  bin object data.
    """
    Bindata=[]
    infosize = os.path.getsize(fileName)
    if infosize>512:
        print('The file size is '+str(infosize)+' bytes, currently only supports the file size is less than 512 bytes')
        sys.exit(1)
    with open(fileName, "rb") as bin_file:
        try:

            data = bin_file.read()
            for eachdata in data:
                Bindata.append(int(eachdata)) 

        except Exception as e:
            bin_file.close()
            print(("\nError: "+fileName+'  format error!!!'))
            print(('Please check '+ fileName+' and try again.\n')) 
            sys.exit(1)
    bin_file.close()
    return Bindata

def Json_Devices_check(JsonData):
    count = 0
    for device in JsonData['Devices']:
        count = count +1        
        #1. Index is 0x00~0xA7
        
        try:
            Index = int(device['Index'])
            if Index < 0 or  Index > 167:
                sys.exit(1)
        except:
            print(("Error: Devices["+str(count)+"] : The value of Index( "+str(device['Index'])+ " is not in 0~167) is invalid,please check."))
            sys.exit(1)
        
        #2. Index is 0x00~0xFF
        try:
            Bifurcation = int(device['Width'])
            if Bifurcation < 0 or  Bifurcation > 255:
                sys.exit(1)
        except:
            print(("Error: Devices["+str(count)+"] : The value of Width( "+str(device['Width'])+ " is not in 0~255) is invalid,please check."))
            sys.exit(1)

        #3. ID is 0~255
        try:
            Idnum = int(device['ID'])
            if Idnum < 0 or  Idnum > 255:
                sys.exit(1)  
        except:
            print(("Error: Devices["+str(count)+"] : The value of ID( "+str(device['ID'])+ " is not in 0~255) is invalid,please check."))
            sys.exit(1)  
        #4. Type is O ,T, P, N
        try:
            Type = str(device['Type'])
            if Type.__len__() != 1:
                sys.exit(1)
            if Type[0] < 'A' or Type[0] > 'Z':
                sys.exit(1)  
        except:
            print(("Error: Devices["+str(count)+"] : The value of Type( "+str(device['Type'])+ " is not in A~Z or lenth error ) is invalid,please check."))
            sys.exit(1)


def Json_Header_check(JsonData):

    Signature=str(JsonData['Header']['Signature'])
    if Signature.__len__() > 4:
        print(("Error: The value of Signature:'"+Signature+ "' is invalid,please check."))
        sys.exit(1)     

    Suite=str(JsonData['Header']['Suite'])
    if Suite.__len__() > 16:
        print(("Error: The value of Suite:'"+Suite+ "' is invalid,please check."))
        sys.exit(1)

def Json_data_check(JsonData):
    #1.
    Json_Devices_check(JsonData)
    #2.
    Json_Header_check(JsonData)

def Json_data_handle(JsonData):
    count = 0
    DataBuf = bytearray()
    for device in JsonData['Devices']:
        count = count +1
        Index = int(device['Index'])
        Bifurcation = int(device['Width'])
        Type = str(device['Type'])
        Idnum = int(device['ID'])
        Type=ord(Type)
        DeviceBuf = bytearray([Index,Bifurcation,Type,Idnum])
        DataBuf.extend(DeviceBuf)
    return DataBuf

def Header_data_handle(JsonData):

    DataBuf = bytearray([ord('O'),ord('P'),ord('O'),ord('T')])
    Signature=str(JsonData['Header']['Signature'])
    if Signature != "TOPO":
        Blank=bytearray((4-Signature.__len__()))
        DataBuf[0:]=Signature
        DataBuf.extend(Blank)

    Version=JsonData['Header']['Version']
    V_Major=int(Version)
    DataBuf.append(V_Major)
    V_Minor=int((Version*10))%10
    DataBuf.append(V_Minor)

    DataBuf.extend([0,0,255,255,255,255,0,0,0,0])

    Suite=str(JsonData['Header']['Suite'])
    Blank=bytearray((16-Suite.__len__()))

    DataBuf.extend(Suite.encode())
    DataBuf.extend(Blank) 
    return DataBuf


def crc32(st):
    crc = zlib.crc32(st)
    if crc > 0:
      return  (crc)
    else:
      return  (~crc ^ 0xffffffff)

def IsEqual(StrList,ByteLits,len):
    for s in range(0,len):
        if int(StrList[s],16)==ByteLits[s]:
            pass
        else:
            return 1
    return 0



def Send_Data(SendData):

    #global EEPROM_OFFSET
    Eeprom_Offset_Write=EEPROM_OFFSET
    SendDataLen=0
    SendDataStr=""
    SendDataPos=0
    print("\nStart data writing ...\n")
    for buf in SendData:
        SendDataStr=SendDataStr+" 0x%02x" %buf
        SendDataLen = SendDataLen +1
        SendDataPos = SendDataPos +1
        if  SendDataPos == SendData.__len__() or SendDataLen  == IPMI_CMD_FRU_WRITE_MAX_LEN:
            try:
                print("Writing data ...")
                SendDataStr=IPMI_CMD_HEADER + " 0x00"+" 0x%02x" %(Eeprom_Offset_Write >> 8 & 0xff )+ " 0x%02x" %(Eeprom_Offset_Write & 0xff) +SendDataStr
                result,resultout=Nettrix_getstatusoutput(SendDataStr)
                if result is not 0:
                    print(resultout)
                    sys.exit(1)
                time.sleep(1)
                print("Verifying Data ...")
                SendDataStr=""
                SendDataStr=IPMI_CMD_HEADER + " 0x%02x" %SendDataLen +" 0x%02x" %(Eeprom_Offset_Write >> 8 & 0xff )+ " 0x%02x" %(Eeprom_Offset_Write & 0xff)
                result,resultout=Nettrix_getstatusoutput(SendDataStr)
                if result is not 0:
                    print("Error :Verify Data Failed!!! ")
                    sys.exit(1)
                time.sleep(1)
                result=IsEqual(str(resultout).split(),SendData[SendDataPos-SendDataLen:SendDataPos],SendDataLen)
                if result is not 0:
                    print("Error :Verify Data Failed!!! ")
                    sys.exit(1)               
                Eeprom_Offset_Write=Eeprom_Offset_Write+SendDataLen
                SendDataLen = 0
                SendDataStr=""
            except:
                print("Error: Data write failed!!!")
                sys.exit(1)
    print("Successfully write data")

def Send_bin_Data(SendData):    
    #global EEPROM_OFFSET
    Eeprom_Offset_Write=EEPROM_OFFSET
    SendDataLen=0
    SendDataStr=""
    SendDataPos=0
    print("\nStart data writing ...\n")
    for buf in SendData:
        SendDataStr=SendDataStr+  " 0x%02x" %int(buf)
        SendDataLen = SendDataLen +1
        SendDataPos = SendDataPos +1
        SendAddrStr=" 0x%02x" %(Eeprom_Offset_Write >> 8 & 0xff )+ " 0x%02x" %(Eeprom_Offset_Write & 0xff)
        #Every time to write 64 byte until end-of-file
        if  SendDataPos == SendData.__len__() or SendDataLen  == IPMI_CMD_FRU_WRITE_MAX_LEN:     
            try:
                print("Writing data ...")
                SendDataStr=IPMI_CMD_HEADER + " 0x00" + SendAddrStr + SendDataStr
                result,resultout=Nettrix_getstatusoutput(SendDataStr)
                SendDataStr=''
                SendDataLen=0
                #Write a page, the address offset 64 bytes
                Eeprom_Offset_Write=Eeprom_Offset_Write+IPMI_CMD_FRU_WRITE_MAX_LEN
            except:
                print("Error: Data write failed!!!")
                sys.exit(1)
    print("Successfully write data")
    sys.exit(0)

def CMD_Send_bin_Data(BinFile):
    BinData=read_Bin_file(BinFile)
    Send_bin_Data(BinData)


def CMD_Signature_Verify(ReadDataBuf):
    #Signature check

    # sys.exit(0)
    if ARGS_SIGNATURE and ARGS_SIGNATURE != "TOPO":
        
        Signature=str(ARGS_SIGNATURE)
        lenth=Signature.__len__()
        if lenth > 4:
            lenth=4
        if  ReadDataBuf[0:lenth]!=Signature[0:lenth]:
            print("Error :Signature Verify Failed!!!")
            sys.exit(1)
    else:
        ReadDataBuf=chr(ReadDataBuf[0])+chr(ReadDataBuf[1])+chr(ReadDataBuf[2])+chr(ReadDataBuf[3])
        if  ReadDataBuf!="OPOT":
            print("ReadDataBuf[0:4]!=OPOT Error :Signature Verify Failed!!!")
            sys.exit(1)

def CMD_Read_BinData(datalen):
    SendDataLen=0
    BMCBinData=""
    SendDataPos=0
    print("datalen:",datalen,type(datalen))
    moredatdalen=" 0x%02x" %(datalen%255 )
    Eeprom_Offset_Write=EEPROM_OFFSET

    for i in range(datalen):
        SendAddrStr=" 0x%02x" %(Eeprom_Offset_Write >> 8 & 0xff )+ " 0x%02x" %(Eeprom_Offset_Write & 0xff)
        SendDataLen=SendDataLen+1
        SendDataPos=SendDataPos+1
        if  SendDataLen  == 255:
            try:
                print("read data ...")
                SendDataStr=IPMI_CMD_HEADER + " 0xff" + SendAddrStr
                result,resultout=Nettrix_getstatusoutput(SendDataStr)
                SendDataLen=0
                Eeprom_Offset_Write=Eeprom_Offset_Write+255
                BMCBinData=BMCBinData+resultout
            except:
                print("Error: Data read failed!!!")
                sys.exit(1)
            print("Successfully read data")
        elif  SendDataPos == datalen:
            try:
                print("read data ...")
                SendDataStr=IPMI_CMD_HEADER +moredatdalen+ SendAddrStr
                result,resultout=Nettrix_getstatusoutput(SendDataStr)
                BMCBinData=BMCBinData+resultout
                SendDataPos=0
            except:
                print("Error: Data read failed!!!")
                sys.exit(1)
            print("Successfully read data")
    BMCBinData=str(BMCBinData).replace(" ", "")
    BMCBinData=str(BMCBinData).replace("\n", "")
    return BMCBinData


def CMD_Check_BinData(BinData): 

    Binstr=""
    BMCstr=CMD_Read_BinData(len(BinData))

    for eachdata in BinData:
        Binstr=Binstr+ "%02x" %eachdata

    print("Binstr:",Binstr,type(Binstr),len(Binstr))
    print("BMCstr:",BMCstr,type(BMCstr),len(BMCstr)) 
    #BMC read data in comparison with bin file data is converted to a string
    result=operator.eq(Binstr, BMCstr)
    if result ==True:
        print("\nInfo :Verify Data Succeeded!!!\n")
        sys.exit(0)
    else:
        print("\nInfo :Verify Data Failed !!!\n")
        sys.exit(1)

def Print_Data(DataBuf):
    counter=0
    PrintBuf=str()
    for data in DataBuf:
        PrintBuf=PrintBuf+" %02X" %data
        counter=counter+1
        if counter%16 == 0 or counter==DataBuf.__len__():
            PrintBuf=PrintBuf+'\n'
    print(PrintBuf)

if __name__ == '__main__':

    import argparse
    parser = argparse.ArgumentParser(description='Arguments for PcieEEpromTool SettingsCase')
    parser.add_argument('-H', '--ip',action='store', help='ip address e.g.,192.168.1.1')
    parser.add_argument('-U', '--username', action='store', help='input username e.g.,admin')
    parser.add_argument('-P', '--password', action='store', help='input password e.g.,admin')
    parser.add_argument('-I', '--interface', action='store', help='input a ipmi interface e.g.,lanplus')
    parser.add_argument('-W', '--write',action='store', help='input a config filename e.g.,setting.json,xxx.bin')
    parser.add_argument('-R', '--read', action='store_true', help='read raw data from BMC.')
    parser.add_argument('-C', '--check', action='store', help='read raw data from BMC and check is right.')
    parser.add_argument('--signature', action='store', help='input Signature for data reading and verification. The default value is TOPO.')
    parser.add_argument('--version',action = 'version',version = '%(prog)s 1.0')
    args = parser.parse_args()
    IPMI_CMD_HEADER=CheckUp_parameters(args,IPMI_CMD_HEADER)

    #0.0 check BMC is right
    try:
        result=os.system(IPMI_CMD_HEADER+IPMI_CMD_MCINFO_CMD)
        if result is not 0:
            sys.exit(1)
    except:
        sys.exit(1)
    else:
        IPMI_CMD_HEADER=IPMI_CMD_HEADER+IPMI_CMD_RAW_HEAD
    time.sleep(1)

    if args.write:
        CMD_Send_bin_Data(args.write)

    if  args.check:
        BinData=read_Bin_file(args.check)
        CMD_Check_BinData(BinData)

    sys.exit(0)