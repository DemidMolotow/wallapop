#!/system/bin/sh

LOGFILE="/data/local/tmp/spoof.log"
ERRLOG="/data/local/tmp/spoof_error.log"

# Если spoof.log уже существует — ничего не делаем
if [ -f "$LOGFILE" ]; then
    exit 0
fi

# Генерация случайных значений
ANDROID_ID=$(cat /dev/urandom | tr -dc 'a-f0-9' | head -c 16)
IMEI="35$(cat /dev/urandom | tr -dc '0-9' | head -c 13)"
SERIAL=$(cat /dev/urandom | tr -dc 'A-Z0-9' | head -c 12)
MAC="02:00:00:$(od -An -N3 -tx1 /dev/urandom | tr ' ' ':' | sed 's/^://')"

# Применение новых значений
settings put secure android_id $ANDROID_ID
echo $IMEI > /data/property/persist.radio.imei

# Только в build.prop, setprop не используем для ro.serialno!
sed -i 's/^ro.product.model=.*/ro.product.model=SM-G991B/' /system/build.prop
sed -i 's/^ro.product.brand=.*/ro.product.brand=samsung/' /system/build.prop
sed -i 's/^ro.product.device=.*/ro.product.device=r0q/' /system/build.prop
sed -i "s/^ro.build.fingerprint=.*/ro.build.fingerprint=samsung\/r0q\/SM-G991B:12\/SP1A.210812.016\/G991BXXU4CVC4:user\/release-keys/" /system/build.prop
sed -i "s/^ro.serialno=.*/ro.serialno=$SERIAL/" /system/build.prop

# Подмена MAC-адреса для существующего интерфейса
IFACE=$(ip link | grep -E 'eth0|wlan0' | awk -F: '{print $2}' | head -n1 | xargs)
if [ -n "$IFACE" ]; then
    ip link set $IFACE down
    ip link set $IFACE address $MAC
    ip link set $IFACE up
else
    echo "No eth0 or wlan0 interface found" >> "$ERRLOG"
fi

# Очистка Google сервисов
pm clear com.google.android.gsf
pm clear com.google.android.gsm
rm -rf /data/data/com.google.android.gsf/databases/gservices.db

# Логирование новых значений
echo "android_id:$ANDROID_ID" > "$LOGFILE"
echo "imei:$IMEI" >> "$LOGFILE"
echo "serial:$SERIAL" >> "$LOGFILE"
echo "mac:$MAC" >> "$LOGFILE"
su
rm /data/local/tmp/spoof.log
chmod 755 /system/bin/spoof.sh
/system/bin/spoof.sh
cat /data/local/tmp/spoof.log
ДОЛЖНЫ БЫТЬ НОВЫЕ ЗНАЧЕНИЯ