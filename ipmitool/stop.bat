ipmitool.exe -H 192.168.1.10 -U toutiao -P toutiao!@# -I lanplus raw 0x3e 0x5c 0x0b 0x01 0x80
timeout /t 5 /nobreak >nul
ipmitool.exe -H 192.168.1.10 -U toutiao -P toutiao!@# -I lanplus raw 0x3e 0x5c 0x0a 0x01 0x80
timeout /t 5 /nobreak >nul
ipmitool.exe -H 192.168.1.10 -U toutiao -P toutiao!@# -I lanplus raw 0x3e 0x5c 0x00 0x01 0x81
timeout /t 5 /nobreak >nul
ipmitool -I lanplus -U toutiao -P 'toutiao!@#' -H 192.168.1.10 raw 0x3e 0x5a 0x81
timeout /t 5 /nobreak >nul
pause