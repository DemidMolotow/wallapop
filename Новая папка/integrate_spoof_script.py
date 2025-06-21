import os
import shutil
import subprocess

# ==== Настройки ====
# Путь к initrd.img
INITRD_IMG = r"C:\Users\Vitalya\Desktop\Новая папка\initrd.img"
# Путь к cpio.exe и gzip.exe (скачай и положи их в эту же папку или укажи другой путь)
CPIo_EXE = r"C:\Users\Vitalya\Desktop\Новая папка\cpio.exe"
GZIP_EXE = r"C:\Users\Vitalya\Desktop\Новая папка\gzip.exe"
# Рабочая папка (может быть прямо на рабочем столе)
WORK_DIR = r"C:\Users\Vitalya\Desktop\Новая папка\initrd_work"
SCRIPT_NAME = "spoof.sh"
SCRIPT_CONTENT = r"""#!/system/bin/sh
ANDROID_ID=$(cat /dev/urandom | tr -dc 'a-f0-9' | head -c 16)
IMEI="35$(cat /dev/urandom | tr -dc '0-9' | head -c 13)"
SERIAL=$(cat /dev/urandom | tr -dc 'A-Z0-9' | head -c 12)
MAC="02:00:00:$(od -An -N3 -tx1 /dev/urandom | tr ' ' ':' | sed 's/^://')"

settings put secure android_id $ANDROID_ID
echo $IMEI > /data/property/persist.radio.imei
setprop ro.serialno $SERIAL

sed -i '/^ro.product.model=/c\\ro.product.model=SM-G991B' /system/build.prop
sed -i '/^ro.product.brand=/c\\ro.product.brand=samsung' /system/build.prop
sed -i '/^ro.product.device=/c\\ro.product.device=r0q' /system/build.prop
sed -i '/^ro.build.fingerprint=/c\\ro.build.fingerprint=samsung/r0q/SM-G991B:12/SP1A.210812.016/G991BXXU4CVC4:user/release-keys' /system/build.prop
sed -i '/^ro.serialno=/c\\ro.serialno=$SERIAL' /system/build.prop

ip link set wlan0 down
ip link set wlan0 address $MAC
ip link set wlan0 up

pm clear com.google.android.gsf
pm clear com.google.android.gms
rm -rf /data/data/com.google.android.gsf/databases/gservices.db

echo "android_id:$ANDROID_ID" > /data/local/tmp/spoof.log
echo "imei:$IMEI" >> /data/local/tmp/spoof.log
echo "serial:$SERIAL" >> /data/local/tmp/spoof.log
echo "mac:$MAC" >> /data/local/tmp/spoof.log
"""

# ==== Подготовка ====
if os.path.exists(WORK_DIR):
    shutil.rmtree(WORK_DIR)
os.makedirs(WORK_DIR)

shutil.copy(INITRD_IMG, os.path.join(WORK_DIR, "initrd.img"))
os.chdir(WORK_DIR)

# ==== Распаковка initrd.img ====
print("Распаковка initrd.img...")
subprocess.check_call([GZIP_EXE, "-d", "initrd.img"])  # Получится файл "initrd"
os.makedirs("unpacked")
with open("initrd", "rb") as f_in, open("unpacked.cpio", "wb") as f_out:
    f_out.write(f_in.read())
subprocess.check_call([CPIo_EXE, "-idmv"], cwd="unpacked", stdin=open("initrd", "rb"))

# ==== Помещение скрипта ====
print("Добавление spoof.sh в /bin ...")
bin_dir = os.path.join(WORK_DIR, "unpacked", "bin")
if not os.path.exists(bin_dir):
    os.makedirs(bin_dir)
with open(os.path.join(bin_dir, SCRIPT_NAME), "w", newline="\n") as f:
    f.write(SCRIPT_CONTENT)

# ==== Добавление вызова скрипта в init.rc ====
rc_path = os.path.join(WORK_DIR, "unpacked", "init.rc")
if os.path.exists(rc_path):
    with open(rc_path, "a", newline="\n") as f:
        f.write(f"\n/bin/{SCRIPT_NAME}\n")
else:
    print("ВНИМАНИЕ: Не найден init.rc! Добавь вызов скрипта в правильный rc-файл вручную.")

# ==== Пересборка initrd ====
print("Сборка нового initrd...")
os.chdir("unpacked")
with open("../initrd_new", "wb") as fout:
    subprocess.check_call([CPIo_EXE, "-o", "-H", "newc"], stdout=fout)
os.chdir("..")
subprocess.check_call([GZIP_EXE, "initrd_new"])

# ==== Готово ====
print("Готово! Новый initrd_new.gz создай как initrd.img и вставь в ISO.")