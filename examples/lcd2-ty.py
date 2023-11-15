#!/usr/bin/python
# -*- coding: UTF-8 -*-
# import chardet
import os
import sys 
import time
import logging
import serial
import re
import psutil 
sys.path.append("..")
from datetime import datetime
from libs import LCD_2inch
from PIL import Image,ImageDraw,ImageFont
from pathlib import Path 
from time import strftime, gmtime



def bytes2human(n):
    """
    >>> bytes2human(10000)  # doctest: +ELLIPSIS
    '9K'
    >>> bytes2human(100001221)  # doctest: +ELLIPSIS
    '95M'
    """
    symbols = ('K', 'M', 'G', 'T', 'P', 'E', 'Z', 'Y')
    prefix = {}
    for i, s in enumerate(symbols):
        prefix[s] = 1 << (i + 1) * 10
    for s in reversed(symbols):
        if n >= prefix[s]:
            value = float(n) / prefix[s]
            return '%.0f' % (value)        
    return "%sB" % n

  #---------------------------------------------------------------------------------------

def bytes2human2(n):
    """
    >>> bytes2human(10000)
    '9K'
    >>> bytes2human(100001221)
    '95M'
    """
    symbols = ('K', 'M', 'G', 'T', 'P', 'E', 'Z', 'Y')
    prefix = {}
    for i, s in enumerate(symbols):
        prefix[s] = 1 << (i + 1) * 10
    for s in reversed(symbols):
        if n >= prefix[s]:
            value = float(n) / prefix[s]
            return '%.1f%s' % (value, s)   
    return "%s B" % n

#======================================================================================


def today_date():
    now = datetime.now()
    today_date = now.strftime("%Y-%m-%d")
    return "%s" \
        % (today_date)

def today_week():
    now = datetime.now()
    today_week = now.strftime("%a")
    return "%s" \
        % (today_week)

def today_time():
    now = datetime.now()
    today_time = now.strftime("%H:%M:%S")
    return "%s" \
        % (today_time)        

#======================================================================================
#======================================================================================

         
def cpu_temp():
    if not hasattr(psutil, "sensors_temperatures"):
        sys.exit("platform not supported")
    temps = psutil.sensors_temperatures()
    if not temps:
        sys.exit("can't read any temperature")
    for name, entries in temps.items():
        for entry in entries:
            return "%.0f°C" \
            % (entry.current)
    
#======================================================================================


def ram_total():
    rt = psutil.virtual_memory()
    return "%s" \
        % (bytes2human2(rt.total))

def ram_used():
    ru = psutil.virtual_memory()
    return "%s" \
        % (bytes2human2(ru.used))

def ram_free():
    rf = psutil.virtual_memory()
    return "%s" \
        % (bytes2human2(rf.total - rf.used))                

def ram_perc():
    rp = psutil.virtual_memory()
    return "%.0f" \
        % (rp.percent)


#======================================================================================


def disk_total(dir):
    dt = psutil.disk_usage(dir)
    return "%s" \
        % (bytes2human2(dt.total))

def disk_used(dir):
    du = psutil.disk_usage(dir)
    return "%s" \
        % (bytes2human2(du.used))

def disk_free(dir):
    df = psutil.disk_usage(dir)
    return "%s" \
        % (bytes2human2(df.free))                

def disk_perc(dir):
    dp = psutil.disk_usage(dir)
    return "%.0f" \
        % (dp.percent)

#======================================================================================


def net_ip(iface):
    """获取ipv4地址"""
    dic = psutil.net_if_addrs()[iface][0]
    if dic.family.name == 'AF_INET':
        return dic.address
    return 'None'


def sent(iface):
    stat = psutil.net_io_counters(pernic=True)[iface]
    return "%s" % \
           (bytes2human2(stat.bytes_sent))


def recv(iface):
    stat = psutil.net_io_counters(pernic=True)[iface]
    return "%s" % \
           (bytes2human2(stat.bytes_recv))


#=========================================================================================


class UPS2: # 串口读取UPS数据
    def __init__(self, port):   # 串口初始化
        self.ser = serial.Serial(port, 9600)  # 串口初始化
        self.data = ""  # 串口数据
        self.oldversion = ""    # 旧版本
        self.oldvin = ""    # 旧输入电压
        self.oldbatcap = "0"    # 旧电池容量
        self.oldvout = "0"  # 旧输出电压

    def get_data(self): # 读取串口数据
        self.count = self.ser.inWaiting()   # 获取串口缓冲区数据
        if self.count != 0: # 如果串口有数据
            self.recv = self.ser.read(self.count)   # 读取缓冲区全部数据
            return self.recv    # 返回读取的数据

    def decode_uart(self):  # 解码串口数据
        self.uart_string = self.get_data()  # 获取串口数据

        if self.uart_string is not None:    # 如果串口数据不为空
            self.data += self.uart_string.decode('ascii', 'ignore') # 解码串口数据
        if len(self.data) > 100:    # 如果串口数据大于100
            self.pattern = r'\$ (.*?) \$'   # 正则表达式
            self.result = re.findall(self.pattern, self.data, re.S) # 正则匹配
            self.data = ""  # 清空串口数据
            self.tmp = self.result[0]   # 获取匹配结果

            self.pattern = r'SmartUPS (.*?),'   # 正则表达式
            self.version = re.findall(self.pattern, self.tmp)   # 正则匹配
            self.oldversion = self.version[0]   # 获取匹配结果

            self.pattern = r',Vin (.*?),'   # 正则表达式
            self.vin = re.findall(self.pattern, self.tmp)   # 正则匹配
            self.oldvin = self.vin[0]   # 获取匹配结果

            self.pattern = r'BATCAP (.*?),'  # 正则表达式
            self.batcap = re.findall(self.pattern, self.tmp)    # 正则匹配
            self.oldbatcap = self.batcap[0] # 获取匹配结果

            self.pattern = r',Vout (.*)'
            self.vout = re.findall(self.pattern, self.tmp)
            self.oldvout = self.vout[0]

            return self.version[0], self.vin[0], self.batcap[0], self.vout[0]   # 返回匹配结果
        else:
            return self.oldversion, self.oldvin, self.oldbatcap, self.oldvout   # 返回旧匹配结果


#==========================================================================================


def fontE(size):    # 英文字体
    font_pathEN = str(Path(__file__).resolve().parent.joinpath('../fonts', 'arialbd.ttf'))
    return ImageFont.truetype(font_pathEN, size)

#==========================================================================================


def main():


    CPU_1cir_x1 = 12                             
    CPU_1cir_y1 = 12                             
    CPU_1cir_radi = 76                           
    CPU_1cir_x2 = CPU_1cir_x1 + CPU_1cir_radi    
    CPU_1cir_y2 = CPU_1cir_y1 + CPU_1cir_radi    

    CPU_cirWidth= 12                             

    CPU_2cir_x1 = CPU_1cir_x1 + CPU_cirWidth                         
    CPU_2cir_y1 = CPU_1cir_y1 + CPU_cirWidth                         
    CPU_2cir_radi = CPU_1cir_radi -  CPU_cirWidth *2                      
    CPU_2cir_x2 = CPU_2cir_x1 + CPU_2cir_radi   
    CPU_2cir_y2 = CPU_2cir_y1 + CPU_2cir_radi   
 
    c0 = psutil.cpu_percent(interval=None)       
    if  c0 < 9.5:                                
        c00 = " %.0f%%" %c0  
    else:
        c00 = "%.0f%%" %c0              

    CPUcir= int(360 * c0 / 100) -90
#---------------------------------------------------------------------------------------------

    RAM_1cir_x1 = 120
    RAM_1cir_y1 = 12
    RAM_1cir_radi = 76 
    RAM_1cir_x2 = RAM_1cir_x1 + RAM_1cir_radi
    RAM_1cir_y2 = RAM_1cir_y1 + RAM_1cir_radi
   
    RAM_cirWidth= 12                           

    RAM_2cir_x1 = RAM_1cir_x1 + RAM_cirWidth                        
    RAM_2cir_y1 = RAM_1cir_y1 + RAM_cirWidth                        
    RAM_2cir_radi = RAM_1cir_radi -  RAM_cirWidth *2                   
    RAM_2cir_x2 = RAM_2cir_x1 + RAM_2cir_radi   
    RAM_2cir_y2 = RAM_2cir_y1 + RAM_2cir_radi    

    r0 = int(ram_perc())
    RAMcir = (360 * r0 / 100) -90

#----------------------------------------------------------------------------------------------

    DISK_1cir_x1 = 230
    DISK_1cir_y1 = 12
    DISK_1cir_radi = 76 
    DISK_1cir_x2 = DISK_1cir_x1 + DISK_1cir_radi
    DISK_1cir_y2 = DISK_1cir_y1 + DISK_1cir_radi

    DISK_cirWidth= 12                        

    DISK_2cir_x1 = DISK_1cir_x1 + DISK_cirWidth                        
    DISK_2cir_y1 = DISK_1cir_y1 + DISK_cirWidth                        
    DISK_2cir_radi = DISK_1cir_radi -  DISK_cirWidth *2                  
    DISK_2cir_x2 = DISK_2cir_x1 + DISK_2cir_radi    
    DISK_2cir_y2 = DISK_2cir_y1 + DISK_2cir_radi  

    d0 = int(disk_perc('/'))
    DISKcir = (360 * d0 / 100) -90

#------------------------------------------------------------------------------------------------

    p_cpu1 = (CPU_1cir_x1,CPU_1cir_y1,CPU_1cir_x2,CPU_1cir_y2)
    p_cpu2 = (CPU_2cir_x1,CPU_2cir_y1,CPU_2cir_x2,CPU_2cir_y2)
    p_cpu_used = (32,35)
    p_cpu_temp = (8,93)

    p_ram1 = (RAM_1cir_x1,RAM_1cir_y1,RAM_1cir_x2,RAM_1cir_y2)
    p_ram2 = (RAM_2cir_x1,RAM_2cir_y1,RAM_2cir_x2,RAM_2cir_y2)
    p_ram_used = (140,35)
    p_ram_free = (112,85)
    p_ram_total = (178,85)

    p_disk1 = (DISK_1cir_x1,DISK_1cir_y1,DISK_1cir_x2,DISK_1cir_y2)
    p_disk2 = (DISK_2cir_x1,DISK_2cir_y1,DISK_2cir_x2,DISK_2cir_y2)
    p_disk_used = (250,35)
    p_disk_free = (220,85)
    p_disk_total = (283,85)

    p_ip = (155,220)
    p_sent = (140,202)
    p_recv = (225,202)

#------------------------------------------------------------------------------------------------

    bg = Image.new("RGBA",( disp.height, disp.width ), "#000066")         # 背景色
    draw = ImageDraw.Draw(bg)
  
  #------------------------------------------------------------------------------------------

  
    draw.rounded_rectangle((0,0,101,117), radius=7, outline="white",width = 2) # CPU
    draw.rounded_rectangle((107,0,209,117), radius=7, outline="white",width = 2) # RAM
    draw.rounded_rectangle((215,0,318,117), radius=7, outline="white",width = 2) # DISK
    draw.rounded_rectangle((0,124,101,238), radius=7, outline="white",width = 2) # UPS info
    draw.rounded_rectangle((107,124,318,175), radius=7, outline="white",width = 2) # Date time 
    draw.rounded_rectangle((107,181,318,238), radius=7, outline="white",width = 2) # IP
    
  #------------------------------------------------------------------------------------------

    draw.ellipse(p_cpu1, fill= '#00FF00')                                   # 圆环 未使用颜色 
    draw.pieslice(p_cpu1, -90, CPUcir, fill = '#FF6666')                    # 圆环 已使用颜色
    draw.ellipse(p_cpu2, fill= '#000066')                                   # 中心环 颜色
    draw.text((4,3),"CPU", font = fontE(13))     
    draw.text(p_cpu_used,"Used\n "+c00, font = fontE(15))     
    draw.text(p_cpu_temp,"Temp : "+cpu_temp(), font = fontE(15))     

    draw.ellipse(p_ram1, fill= '#00FF00')  # 圆环 未使用颜色
    draw.pieslice(p_ram1, -90, RAMcir, fill = '#FF6666')    # 圆环 已使用颜色
    draw.ellipse(p_ram2, fill= '#000066') 
    draw.text((112,3),"RAM", font = fontE(13))     
    draw.text(p_ram_used,"Used\n "+ram_perc()+'%', font = fontE(15))     
    draw.text(p_ram_free,"Free\n"+ram_free(), font = fontE(12))     
    draw.text(p_ram_total,"Total\n"+ram_total(), font = fontE(12))

    draw.ellipse(p_disk1, fill= '#00FF00')   
    draw.pieslice(p_disk1, -90, DISKcir, fill = '#FF6666')
    draw.ellipse(p_disk2, fill= '#000066') 
    draw.text((220,3),"DISK", font = fontE(13))     
    draw.text(p_disk_used,"Used\n "+disk_perc('/')+'%', font = fontE(15))     
    draw.text(p_disk_free,"Free\n"+disk_free('/'), font = fontE(12))     
    draw.text(p_disk_total," Total\n"+disk_total('/'), font = fontE(12))     

    draw.text((112,127),"DATETIME", font = fontE(13))     
    draw.text((238,127),today_date(), font = fontE(14))     
    draw.text((202,127),today_week(), font = fontE(14))     
    draw.text((160,144),today_time(), font = fontE(26))     

    draw.text((112,184),"NETWORK", font = fontE(13))     
    draw.text((204,184),"Xiaochen CHINA", fill= 'white', font = fontE(12))
    # 有线网卡优先显示
    if net_ip('eth0') == 'None':
        draw.text(p_ip,'IP : '+net_ip('wlan0'), font = fontE(13))
        draw.text(p_sent,'▲  '+sent('wlan0'), fill ='#00CCFF', font = fontE(13))
        draw.text(p_recv,'▼  '+recv('wlan0'), fill = '#00FF00', font = fontE(13))
    else:
        draw.text(p_ip,'IP : '+net_ip('eth0'), font = fontE(13))
        draw.text(p_sent,'▲  '+sent('eth0'), fill ='#00CCFF', font = fontE(13))
        draw.text(p_recv,'▼  '+recv('eth0'), fill = '#00FF00', font = fontE(13))


  #------------------------------------------------------------------------------------------
 
    
    global ups  # 串口读取UPS数据
    version, vin, batcap, vout = ups.decode_uart()  # 串口读取UPS数据
 
    draw.text((4, 127),"UPS", font = fontE(13))     # UPS
    # draw.text((6, 151),"Version: "+version, font = fontE(11))

    
    global at
    global bt

    if vin == "NG": # 如果输入电压为NG

        bt = time.time()    # 获取当前时间
        nt = time.time() - at   # 计算时间差
        show_time = strftime("%H:%M:%S", gmtime(nt))    # 格式化时间差
        draw.text((6, 167),"Power \nNOT connected !", font=fontE(11), fill="red")   # 显示电源未连接
        
    else:

        at = time.time()    # 获取当前时间
        nt = time.time() - bt   # 计算时间差
        show_time = strftime("%H:%M:%S", gmtime(nt))    # 格式化时间差
        draw.text((6, 167),"Power \nconnected !", font=fontE(11), fill="#99FF00")   # 显示电源已连接
    
    
    draw.text((6, 151),"UpTime: "+show_time, font = fontE(11))
    draw.text((6, 198),"Capacity: "+batcap+"%", font = fontE(11))       
    draw.text((6, 215),"Voltage: "+vout+" mV", font = fontE(11))    
  
  #------------------------------------------------------------------------------------------
  
    bg = bg.rotate(0) 
    disp.ShowImage(bg)    
  
#==========================================================================================

ups = UPS2("/dev/ttyAMA0")  # 串口读取UPS数据

version, vin, batcap, vout = ups.decode_uart()
if vin == "NG":
    at = time.time() 
    
else:
    bt = time.time() 


if __name__ == "__main__":

    disp = LCD_2inch.LCD_2inch()
    disp.Init()
    disp.clear()    
    while True:
        main()
        time.sleep(0.5)

