#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  installation_thread.py
#  
#  Copyright 2013 Cinnarch
#  
#  This program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 2 of the License, or
#  (at your option) any later version.
#  
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#  
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software
#  Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
#  MA 02110-1301, USA.
#  
#  Cinnarch Team:
#   Alex Filgueira (faidoc) <alexfilgueira.cinnarch.com>
#   Raúl Granados (pollitux) <raulgranados.cinnarch.com>
#   Gustau Castells (karasu) <karasu.cinnarch.com>
#   Kirill Omelchenko (omelcheck) <omelchek.cinnarch.com>
#   Marc Miralles (arcnexus) <arcnexus.cinnarch.com>
#   Alex Skinner (skinner) <skinner.cinnarch.com>

import threading
import subprocess
import os
import sys

from config import installer_settings

# Insert the src/pacman directory at the front of the path.
base_dir = os.path.dirname(__file__) or '.'
parted_dir = os.path.join(base_dir, 'pacman')
sys.path.insert(0, parted_dir)

import misc
import transaction

_autopartition_script = 'auto_partition.sh'

class InstallationThread(threading.Thread):
    def __init__(self, method, mount_devices):
        threading.Thread.__init__(self)

        self.method = method
        self.mount_devices = mount_devices
        
        print(mount_devices)
        
        self.root = mount_devices["/"]
        print("Root device : %s" % self.root)

        self.running = True
        self.error = False
        
        self.auto_partition_script_path = \
            os.path.join(installer_settings["CNCHI_DIR"], "scripts", _autopartition_script)
    
    @misc.raise_privileges    
    def run(self):
        ## Create and format partitions if we're in automatic mode
        if method == "automatic":
            try:
                if os.path.exists(self.script_path):
                       subprocess.Popen(["/bin/bash", self.script_path, self.root])
            except subprocess.FileNotFoundError as e:
                self.error = True
                print (_("Can't execute the auto partition script"))
            except subprocess.CalledProcessError as e:
                self.error = True
                print (_("subprocess CalledProcessError.output = %s") % e.output)

        ## Do real installation here
        
        # Extracted from /arch/setup script
        
        dest_dir = "/INSTALL"
        kernel_pkg = "linux"
        vmlinuz = "vmlinuz-%s" % kernel_pkg
        initramfs = "initramfs-%s" % kernel_pkg       
        pacman = "powerpill --root %s --config /tmp/pacman.conf --noconfirm --noprogressbar" % dest_dir
        
        
        
        
        
        self.chroot_mount(dest_dir)
        

        self.running = False
    
    def chroot_mount(self, dest_dir):
        dirs = [ "/sys", "/proc", "/dev" ]
        for d in dirs:
            mydir = os.path.join(dest_dir, d)
            if not os.path.exists(mydir):
                os.makedirs(mydir)

        mydir = os.path.join(dest_dir, "/sys")
        subprocess.Popen(["mount", "-t", "sysfs", "sysfs", mydir])
        subprocess.Popen(["chmod", "555", mydir])

        mydir = os.path.join(dest_dir, "/proc")
        subprocess.Popen(["mount", "-t", "proc", "proc", mydir])
        subprocess.Popen(["chmod", "555", mydir])

        mydir = os.path.join(dest_dir, "/dev")
        subprocess.Popen(["mount", "-o", "bind", "/dev", mydir])

        

    def is_running(self):
        return self.running

    def is_ok(self):
        return not self.error
        
'''

#!/bin/bash
INSTALLER_VERSION=0.7.2

TEXTDOMAIN=cli_installer
# we rely on some output which is parsed in english!
#unset LANG
source /etc/cinnarch/functions

ANSWER="/tmp/.setup"
TITLE=$"Cinnarch Installation - v$INSTALLER_VERSION"
# use the first VT not dedicated to a running console
LOG="/dev/tty6"

# don't use /mnt because it's intended to mount other things there!
DESTDIR="/install"
EDITOR=""
_BLKID="blkid -c /dev/null"

# name of kernel package
KERNELPKG="linux"
# name of the kernel image
VMLINUZ="vmlinuz-${KERNELPKG}"
# name of the initramfs filesystem
INITRAMFS="initramfs-${KERNELPKG}"

# detect systemd running
[[ "$(cat /proc/cmdline | grep -w init=/bin/systemd)" ]] && SYSTEMD="0"
# abstract the common pacman args
PACMAN="powerpill --root ${DESTDIR} --config /tmp/pacman.conf --noconfirm --noprogressbar"
# downloader
DLPROG="wget"
PACKAGES=""

dialog --backtitle "${TITLE}" --aspect 15 --infobox $"Checking your connection..." 4 35
NETWORK_ALIVE=`ping -c1 google.com 2>&1 | grep unknown`

# destination of blockdevices in /sys
block="/sys/block"

# partitions
PART_ROOT=""
ROOTFS=""

# Localization parameters
CINNARCHVAR="$(kernel_cmdline cinnarchvar lang:en_US,keymap:en_US)"
KEYMAP="$(echo "$CINNARCHVAR" | cut -d, -f2 | cut -d: -f2)"
LOCALE="$(echo "$CINNARCHVAR" | cut -d, -f1 | cut -d: -f2)"

# Mylex DAC960 PCI RAID controller, Compaq Next Generation Drive Array, 
# Compaq Intelligent Drive Array
EXTRA_CONTROLLER="rd cciss ida"

# install stages
S_SRC=0         # choose install medium
S_NET=0         # network configuration
S_CLOCK=0       # clock and timezone
S_PART=0        # partitioning
S_MKFS=0        # formatting
S_MKFSAUTO=0    # auto fs part/formatting
S_SELECT=0      # package selection
S_INSTALL=0     # package installation
S_CONFIG=0      # configuration editing
S_GRUB=0       # using grub(2)

# menu item tracker- autoselect the next item
NEXTITEM=""

# DIALOG()
# an el-cheapo dialog wrapper
#
# parameters: see dialog(1)
# returns: whatever dialog did
DIALOG() {
    dialog --backtitle "${TITLE}" --aspect 15 "$@"
    return $?
}

# DIALOG() taken from aif installer
# an el-cheapo dialog wrapper
#
# parameters: see dialog(1)
# returns: whatever dialog did
_checklist_dialog()
{
    dialog --backtitle "$TITLE" --aspect 15 "$@" 3>&1 1>&2 2>&3 3>&-
}



# chroot_mount()
# prepares target system as a chroot
#
chroot_mount()
{
    [[ -e "${DESTDIR}/sys" ]] || mkdir -m 555 "${DESTDIR}/sys"
    [[ -e "${DESTDIR}/proc" ]] || mkdir -m 555 "${DESTDIR}/proc"
    [[ -e "${DESTDIR}/dev" ]] || mkdir "${DESTDIR}/dev"
    mount -t sysfs sysfs "${DESTDIR}/sys"
    mount -t proc proc "${DESTDIR}/proc"
    mount -o bind /dev "${DESTDIR}/dev"
    chmod 555 "${DESTDIR}/sys"
    chmod 555 "${DESTDIR}/proc"
}

# chroot_umount()
# tears down chroot in target system
#
chroot_umount()
{
    umount "${DESTDIR}/proc"
    umount "${DESTDIR}/sys"
    umount "${DESTDIR}/dev"
}

getfstype()
{
    echo "$(${_BLKID} -p -i -s TYPE -o value ${1})"
}

# getfsuuid()
# converts /dev devices to FSUUIDs
#
# parameters: device file
# outputs:    FSUUID on success
#             nothing on failure
# returns:    nothing
getfsuuid()
{
    echo "$(${_BLKID} -p -i -s UUID -o value ${1})"
}

# parameters: device file
# outputs:    LABEL on success
#             nothing on failure
# returns:    nothing
getfslabel()
{
    echo "$(${_BLKID} -p -i -s LABEL -o value ${1})"
}

getpartuuid()
{
    echo "$(${_BLKID} -p -i -s PART_ENTRY_UUID -o value ${1})"
}

getpartlabel()
{
    echo "$(${_BLKID} -p -i -s PART_ENTRY_NAME -o value ${1})"
}

# list eth devices with mac adress
net_interfaces() {
    for i in $(ls /sys/class/net | grep eth); do 
        echo "$i $(cat /sys/class/net/$i/address)"
    done
}

# activate_dmraid()
# activate dmraid devices
activate_dmraid()
{
    if [[ -e /sbin/dmraid ]]; then
        DIALOG --infobox $"Activating dmraid arrays..." 0 0
        /sbin/dmraid -ay -I -Z >/dev/null 2>&1
    fi
}

# activate_lvm2
# activate lvm2 devices
activate_lvm2()
{
    ACTIVATE_LVM2=""
    if [[ -e /sbin/lvm ]]; then
        OLD_LVM2_GROUPS=${LVM2_GROUPS}
        OLD_LVM2_VOLUMES=${LVM2_VOLUMES}
        DIALOG --infobox $"Scanning logical volumes..." 0 0
        /sbin/lvm vgscan --ignorelockingfailure >/dev/null 2>&1
        DIALOG --infobox $"Activating logical volumes..." 0 0
        /sbin/lvm vgchange --ignorelockingfailure --ignoremonitoring -ay >/dev/null 2>&1
        LVM2_GROUPS="$(vgs -o vg_name --noheading 2>/dev/null)"
        LVM2_VOLUMES="$(lvs -o vg_name,lv_name --noheading --separator - 2>/dev/null)"
        [[ "${OLD_LVM2_GROUPS}" = "${LVM2_GROUPS}" && "${OLD_LVM2_GROUPS}" = "${LVM2_GROUPS}" ]] && ACTIVATE_LVM2="no"
    fi
}

# activate_raid
# activate md devices
activate_raid()
{
    ACTIVATE_RAID=""
    if [[ -e /sbin/mdadm ]]; then
        DIALOG --infobox $"Activating RAID arrays..." 0 0
        /sbin/mdadm --assemble --scan >/dev/null 2>&1 || ACTIVATE_RAID="no"
    fi
}

# activate_luks
# activate luks devices
activate_luks()
{
    ACTIVATE_LUKS=""
    if [[ -e /usr/sbin/cryptsetup ]]; then
        DIALOG --infobox $"Scanning for luks encrypted devices..." 0 0
        if [[ "$(${_BLKID} | grep "TYPE=\"crypto_LUKS\"")" ]]; then
            for PART in $(${_BLKID} | grep "TYPE=\"crypto_LUKS\"" | sed -e 's#:.*##g'); do
                # skip already encrypted devices, device mapper!
                OPEN_LUKS=""
                for devpath in $(ls /dev/mapper 2>/dev/null | grep -v control); do
                    [[ "$(cryptsetup status ${devpath} | grep ${PART})" ]] && OPEN_LUKS="no"
                done
                if ! [[ "${OPEN_LUKS}" = "no" ]]; then
                    RUN_LUKS=""
                    DIALOG --yesno $"Setup detected luks encrypted device, do you want to activate ${PART} ?" 0 0 && RUN_LUKS="1"
                    [[ "${RUN_LUKS}" = "1" ]] && _enter_luks_name && _enter_luks_passphrase && _opening_luks
                    [[ "${RUN_LUKS}" = "" ]] && ACTIVATE_LUKS="no"
                else
                    ACTIVATE_LUKS="no"
                fi
            done
        else
            ACTIVATE_LUKS="no"
        fi
    fi
}

# activate_special_devices()
# activate special devices:
# activate dmraid, lvm2 and raid devices, if not already activated during bootup!
# run it more times if needed, it can be hidden by each other!
activate_special_devices()
{
    ACTIVATE_RAID=""
    ACTIVATE_LUKS=""
    ACTIVATE_LVM2=""
    activate_dmraid
    while ! [[ "${ACTIVATE_LVM2}" = "no" && "${ACTIVATE_RAID}" = "no"  && "${ACTIVATE_LUKS}" = "no" ]]; do
        activate_raid
        activate_lvm2
        activate_luks
    done
}


# destdir_mounts()
# check if PART_ROOT is set and if something is mounted on ${DESTDIR}
destdir_mounts(){
    # Don't ask for filesystem and create new filesystems
    ASK_MOUNTPOINTS=""
    PART_ROOT=""
    # check if something is mounted on ${DESTDIR}
    PART_ROOT="$(mount | grep "${DESTDIR} " | cut -d' ' -f 1)"
    # Run mountpoints, if nothing is mounted on ${DESTDIR}
    if [[ "${PART_ROOT}" = "" ]]; then
        DIALOG --msgbox "Setup couldn't detect mounted partition(s) in ${DESTDIR}, please set mountpoints first." 0 0
        mountpoints || return 1
    fi
}

# lists default linux blockdevices
default_blockdevices() {
    # ide devices
    for dev in $(ls ${block} 2>/dev/null | egrep '^hd'); do
        if [[ "$(cat ${block}/${dev}/device/media)" = "disk" ]]; then
            if ! [[ "$(cat ${block}/${dev}/size)" = "0" ]]; then
                if ! [[ "$(cat /proc/mdstat 2>/dev/null | grep "${dev}\[")" || "$(dmraid -rc | grep /dev/${dev})" ]]; then
                    echo "/dev/${dev}"
                    [[ "${1}" ]] && echo ${1}
                fi
            fi
        fi
    done
    #scsi/sata devices, and virtio blockdevices (/dev/vd*)
    for dev in $(ls ${block} 2>/dev/null | egrep '^[sv]d'); do
        # virtio device doesn't have type file!
        blktype="$(cat ${block}/${dev}/device/type 2>/dev/null)"
        if ! [[ "${blktype}" = "5" ]]; then
            if ! [[ "$(cat ${block}/${dev}/size)" = "0" ]]; then
                if ! [[ "$(cat /proc/mdstat 2>/dev/null | grep "${dev}\[")" || "$(dmraid -rc | grep /dev/${dev})" ]]; then
                    echo "/dev/${dev}"
                    [[ "${1}" ]] && echo ${1}
                fi
            fi
        fi
    done
}

# lists additional linux blockdevices
additional_blockdevices() {
    # Include additional controllers:
    # Mylex DAC960 PCI RAID controller, Compaq Next Generation Drive Array, 
    # Compaq Intelligent Drive Array
    for i in ${EXTRA_CONTROLLER}; do
        for dev in $(ls ${block} 2>/dev/null | egrep "^${i}"); do
            for k in $(ls ${block}/${dev} 2>/dev/null | egrep "${dev}*p"); do
                if [[ -d "${block}/${dev}/${k}" ]]; then
                    echo "/dev/${i}/$(echo ${dev} | sed -e 's#.*\!##g')"
                    [[ "${1}" ]] && echo ${1}
                    break
                fi
            done
        done
    done
    # Include MMC devices
    for dev in $(ls ${block} 2>/dev/null | egrep '^mmcblk'); do
        for i in $(ls ${block}/${dev} 2>/dev/null | egrep ${dev}p); do 
            if [[ -d "${block}/${dev}/${i}" ]]; then 
                echo "/dev/${dev}"
                [[ "${1}" ]] && echo ${1}
                break
            fi
        done
    done
}

# lists additional linux blockdevices partitions
additional_blockdevices_partitions() {
    # Mylex DAC960 PCI RAID controller, Compaq Next Generation Drive Array, 
    # Compaq Intelligent Drive Array
    for k in ${EXTRA_CONTROLLER}; do
        for dev in $(ls ${block} 2>/dev/null | egrep "^${k}"); do
            for i in $(ls ${block}/${dev} 2>/dev/null | egrep "${dev}*p"); do
                if [[ -d "${block}/${dev}/${i}" ]]; then
                    disk="${k}/$(echo ${dev} | sed -e 's#.*\!##g')"
                    part="${k}/$(echo ${i} | sed -e 's#.*\!##g')"
                    # exclude checks:
                    #- part of raid device
                    #  $(cat /proc/mdstat 2>/dev/null | grep ${part})
                    #- part of lvm2 device
                    #  $(${_BLKID} -p -i -o value -s TYPE /dev/${part} | grep "LVM2_member")
                    #- part of luks device
                    #  $(${_BLKID} -p -i -o value -s TYPE /dev/${part} | grep "crypto_LUKS")
                    #- extended partition on device
                    #  $(sfdisk -c /dev/${disk} $(echo ${part} | sed -e "s#${disk}\p##g" 2>/dev/null | grep "5")
                    #- bios_grub partitions
                    # $(echo ${part} | grep "[a-z]$(parted /dev/${disk} print | grep bios_grub | cut -d " " -f 2)$")
                    if ! [[ "$(cat /proc/mdstat 2>/dev/null | grep ${part})" || "$(${_BLKID} -p -i -o value -s TYPE /dev/${part} | grep "LVM2_member")" || "$(${_BLKID} -p -i -o value -s TYPE /dev/${part} | grep "crypto_LUKS")" || "$(sfdisk -c /dev/${disk} $(echo ${part} | sed -e "s#${disk}\p##g") 2>/dev/null | grep "5")" || "$(echo ${part} | grep "[a-z]$(parted /dev/${disk} print | grep bios_grub | cut -d " " -f 2)$")" ]]; then
                        echo "/dev/${part}"
                        [[ "${1}" ]] && echo ${1}
                    fi
                fi
            done
        done
    done
    # Include MMC devices
    for dev in $(ls ${block} 2>/dev/null | egrep '^mmcblk'); do
        for i in $(ls ${block}/${dev} 2>/dev/null | egrep ${dev}p); do 
            if [[ -d "${block}/${dev}/${i}" ]]; then
                # exclude checks:
                #- part of raid device
                #  $(cat /proc/mdstat 2>/dev/null | grep ${i})
                #- part of lvm2 device
                #  $(${_BLKID} -p -i -o value -s TYPE /dev/${i} | grep "LVM2_member")
                #- part of luks device
                #  $(${_BLKID} -p -i -o value -s TYPE /dev/${i} | grep "crypto_LUKS")
                #- extended partition on device
                #  $(sfdisk -c /dev/${dev} $(echo ${i} | sed -e "s#${dev}\p##g" 2>/dev/null | grep "5")
                #- bios_grub partitions
                # $(echo ${i} | grep "[a-z]$(parted /dev/${dev} print | grep bios_grub | cut -d " " -f 2)$")
                if ! [[ "$(cat /proc/mdstat 2>/dev/null | grep ${i})" || "$(${_BLKID} -p -i -o value -s TYPE /dev/${i} | grep "LVM2_member")" || $(${_BLKID} -p -i -o value -s TYPE /dev/${i} | grep "crypto_LUKS") || "$(sfdisk -c /dev/${dev} $(echo ${i} | sed -e "s#${dev}\p##g") 2>/dev/null | grep "5")" || "$(echo ${i} | grep "[a-z]$(parted /dev/${dev} print | grep bios_grub | cut -d " " -f 2)$")" ]]; then
                    echo "/dev/${i}"
                    [[ "${1}" ]] && echo ${1}
                fi
            fi
        done
    done
}

# list none partitionable raid md devices
raid_devices() {
    for devpath in $(ls ${block} 2>/dev/null | egrep '^md'); do
        if ! [[ "$(ls ${block}/${devpath} 2>/dev/null | egrep ${devpath}p)" ]]; then 
            # exlude md partitions which are part of lvm or luks
            if ! [[ "$(${_BLKID} -p -i /dev/${devpath} | grep "TYPE=\"LVM2_member\"")" || "$(${_BLKID} -p -i /dev/${devpath} | grep "TYPE=\"crypto_LUKS\"")" ]]; then
                    echo "/dev/${devpath}"
                    [[ "${1}" ]] && echo ${1}
            fi
        fi
    done
}

# lists default linux partitionable raid devices
partitionable_raid_devices() {
    for dev in $(ls ${block} 2>/dev/null | egrep '^md'); do
        for i in $(ls ${block}/${dev} 2>/dev/null | egrep "${dev}\!*p"); do 
            if [[ -d "${block}/${dev}/${i}" ]]; then 
                echo "/dev/${dev}"
                [[ "${1}" ]] && echo ${1}
                break
            fi
        done
    done
}

# lists default linux partitionable raid devices
partitionable_raid_devices_partitions() {
    for dev in $(ls ${block} 2>/dev/null | egrep '^md'); do
        for i in $(ls ${block}/${dev} 2>/dev/null | egrep ${dev}p); do 
            if [[ -d "${block}/${dev}/${i}" ]]; then
                # exlude md partitions which are part of lvm or luks
                if ! [[ "$(${_BLKID} -p -i /dev/${i} | grep "TYPE=\"LVM2_member\"")" || ! "$(${_BLKID} -p -i /dev/${i} | grep "TYPE=\"crypto_LUKS\"")" ]]; then
                    echo "/dev/${i}"
                    [[ "${1}" ]] && echo ${1}
                fi
            fi
        done
    done
}

# lists default linux dmraid devices
dmraid_devices() {
    if [[ -d /dev/mapper ]]; then
        for fakeraid in $(dmraid -s -c); do
                if [[ "$(echo ${fakeraid} | grep '_')" ]]; then
                    echo "/dev/mapper/${fakeraid}"
                    [[ "${1}" ]] && echo ${1}
                fi
        done
    fi
}

# check_dm_devices
# - remove part of encrypted devices
# - remove part of lvm
# - remove part ot raid
check_dm_devices() {
    for devpath in $(ls /dev/mapper 2>/dev/null | grep -v control); do
        k="$(${_BLKID} -p -i /dev/mapper/${devpath} 2>/dev/null | grep "TYPE=\"crypto_LUKS\"" | sed -e 's#:.*##g')"
        partofcrypt="${partofcrypt} ${k}"
    done
    for devpath in $(ls /dev/mapper 2>/dev/null | grep -v control); do
        k="$(${_BLKID} -p -i /dev/mapper/${devpath} 2>/dev/null | grep "TYPE=\"LVM2_member\"" | sed -e 's#:.*##g')"
        partoflvm="${partoflvm} ${k}"
    done
    for devpath in $(ls /dev/mapper 2>/dev/null | grep -v control); do
        k="$(${_BLKID} -p -i /dev/mapper/${devpath} 2>/dev/null | grep "TYPE=\"linux_raid_member\"" | sed -e 's#:.*##g')"
        partofraid="${partofraid} ${k}"
    done
}

# dm_devices
# - show device mapper devices 
dm_devices() {
    check_dm_devices
    for i in $(dmraid -s -c); do
        EXCLUDE_DMRAID=""
        if [[ "$(echo ${i} | grep '_')" ]]; then
             EXCLUDE_DMRAID="${EXCLUDE_DMRAID} -e ${i} "
        fi
    done
    if [[ -d /dev/mapper ]]; then
        for devpath in $(ls /dev/mapper 2>/dev/null | grep -v -e control ${EXCLUDE_DMRAID}); do
            if ! [[ "$(ls ${partofcrypt} 2>/dev/null | grep /dev/mapper/${devpath}$)" || "$(ls ${partoflvm} 2>/dev/null | grep /dev/mapper/${devpath}$)" || "$(ls ${partofraid} 2>/dev/null | grep /dev/mapper/${devpath}$)" ]]; then
                echo "/dev/mapper/${devpath}"
                [[ "${1}" ]] && echo ${1}
            fi
        done
    fi
}

# dmraid_partitions
# - show dmraid partitions
dmraid_partitions() {
    check_dm_devices
    if [[ -d /dev/mapper ]]; then
        for fakeraid in $(dmraid -s -c); do
            if [[ "$(echo ${fakeraid} | grep '_')" ]]; then
                for k in $(ls /dev/mapper/${fakeraid}*); do
                    devpath=$(basename ${k})
                    if ! [[ "$(dmraid -s -c | grep ${devpath}$)" || "$(ls ${partofcrypt} 2>/dev/null | grep /dev/mapper/${devpath}$)" || "$(ls ${partoflvm} 2>/dev/null | grep /dev/mapper/${devpath}$)" || "$(ls ${partofraid} 2>/dev/null | grep /dev/mapper/${devpath}$)" ]]; then
                        echo "/dev/mapper/${devpath}"
                        [[ "${1}" ]] && echo ${1}
                    fi
                done
            fi
        done
    fi
}

# do sanity checks on partitions, argument comes ${devpath} loop
default_partition_check() {
        disk=$(basename ${devpath})
        for part in $(ls ${block}/${disk} 2>/dev/null | egrep -v ^${disk}p | egrep ^${disk}); do
            # exclude checks:
            #- part of raid device
            #  $(cat /proc/mdstat 2>/dev/null | grep ${part})
            #- part of lvm2 device
            #  $(${_BLKID} -p -i -o value -s TYPE /dev/${part} | grep "LVM2_member")
            #- part of luks device
            #  $(${_BLKID} -p -i -o value -s TYPE /dev/${part} | grep "crypto_LUKS")
            #- extended partition
            #  $(sfdisk -c /dev/${disk} $(echo ${part} | sed -e "s#${disk}##g") 2>/dev/null | grep "5")
            #- extended partition on raid partition device and mmc device
            #  $(sfdisk -c /dev/${disk} $(echo ${part} | sed -e "s#${disk}\p##g" 2>/dev/null | grep "5")
            #- bios_grub partitions
            # $(echo ${part} | grep "[a-z]$(parted /dev/${disk} print | grep bios_grub | cut -d " " -f 2)$")
            if ! [[ "$(cat /proc/mdstat 2>/dev/null | grep ${part})" || "$(${_BLKID} -p -i -o value -s TYPE /dev/${part} | grep "LVM2_member")" || "$(${_BLKID} -p -i -o value -s TYPE /dev/${part} | grep "crypto_LUKS")" || "$(sfdisk -c /dev/${disk} $(echo ${part} | sed -e "s#${disk}##g") 2>/dev/null | grep "5")" || "$(sfdisk -c /dev/${disk} $(echo ${part} | sed -e "s#${disk}\p##g") 2>/dev/null | grep "5")" || "$(echo ${part} | grep "[a-z]$(parted /dev/${disk} print | grep bios_grub | cut -d " " -f 2)$")" ]]; then
                if [[ -d ${block}/${disk}/${part} ]]; then
                    echo "/dev/${part}"
                    [[ "${1}" ]] && echo ${1}
                fi
            fi
        done
}

finddisks() {
    default_blockdevices ${1}
    additional_blockdevices ${1}
    dmraid_devices ${1}
    partitionable_raid_devices ${1}
}

findpartitions() {
    for devpath in $(finddisks); do
        default_partition_check ${1}
    done
    additional_blockdevices_partitions ${1}
    dm_devices ${1}
    dmraid_partitions ${1}
    raid_devices ${1}
    partitionable_raid_devices_partitions ${1}
}

# don't check on raid devices!
findbootloaderdisks() {
    if ! [[ "${USE_DMRAID}" = "1" ]]; then
        default_blockdevices ${1}
        additional_blockdevices ${1}
    else
        dmraid_devices ${1}
    fi
}

# don't list raid devices, lvm2 and devicemapper!
findbootloaderpartitions() {
    if ! [[ "${USE_DMRAID}" = "1" ]]; then
        for devpath in $(findbootloaderdisks); do
            default_partition_check ${1}
        done
        additional_blockdevices_partitions ${1}
    else
        dmraid_partitions ${1}
    fi
}

# freeze and unfreeze xfs, as hack for grub(2) installing
freeze_xfs() {
    sync
    if [[ -x /usr/sbin/xfs_freeze ]]; then
        if [[ "$(cat /proc/mounts | grep "${DESTDIR}/boot " | grep " xfs ")" ]]; then
            /usr/sbin/xfs_freeze -f ${DESTDIR}/boot >/dev/null 2>&1
            /usr/sbin/xfs_freeze -u ${DESTDIR}/boot >/dev/null 2>&1
        fi
        if [[ "$(cat /proc/mounts | grep "${DESTDIR} " | grep " xfs ")" ]]; then
            /usr/sbin/xfs_freeze -f ${DESTDIR} >/dev/null 2>&1
            /usr/sbin/xfs_freeze -u ${DESTDIR} >/dev/null 2>&1
        fi
    fi
}

mapdev() {
    partition_flag=0
    device_found=0
    # check if we use hd sd  or vd device
    if ! [[ "$(echo ${1} | grep /dev/sd)" || "$(echo ${1} | grep /dev/hd)" || "$(echo ${1} | grep /dev/vd)" ]]; then
        linuxdevice=$(echo ${1} | sed -e 's#p[0-9].*$##')
    else
        linuxdevice=$(echo ${1} | sed -e 's#[0-9].*$##g')
    fi
    if ! [[ "$(echo ${1} | grep /dev/sd)" || "$(echo ${1} | grep /dev/hd)" || "$(echo ${1} | grep /dev/vd)" ]]; then
        if [[ "$(echo ${1} | egrep 'p[0-9].*$')" ]]; then
            pnum=$(echo ${1} | sed -e 's#.*p##g')
            partition_flag=1
        fi
    else
        if [[ "$(echo ${1} | egrep '[0-9]$')" ]]; then
            # /dev/hdXY
            pnum=$(echo ${1} | cut -b9-)
            partition_flag=1
        fi
    fi
    for  dev in ${devs}; do
        if [[ "(" = $(echo ${dev} | cut -b1) ]]; then
            grubdevice="${dev}"
        else
            if [[ "${dev}" = "${linuxdevice}" ]]; then
                device_found=1
                break
            fi
        fi
    done
    if [[ "${device_found}" = "1" ]]; then
        if [[ "${partition_flag}" = "0" ]]; then
            echo "${grubdevice}"
        else
            grubdevice_stringlen=${#grubdevice}
            grubdevice_stringlen=$((${grubdevice_stringlen} - 1))
            grubdevice=$(echo ${grubdevice} | cut -b1-${grubdevice_stringlen})
            echo "${grubdevice},${pnum})"
        fi
    else
        echo "DEVICE NOT FOUND"
    fi
}

printk()
{
    case ${1} in
        "on")  echo 4 >/proc/sys/kernel/printk ;;
        "off") echo 0 >/proc/sys/kernel/printk ;;
    esac
}

getdest() {
    [[ "${DESTDIR}" ]] && return 0
    DIALOG --inputbox "Enter the destination directory where your target system is mounted" 8 65 "/install" 2>${ANSWER} || return 1
    DESTDIR=$(cat ${ANSWER})
}

# geteditor()
# prompts the user to choose an editor
# sets EDITOR global variable
#
geteditor() {
    if ! [[ "${EDITOR}" ]]; then
        DIALOG --menu $"Select a Text Editor to Use" 10 35 3 \
        "1" "nano (easier)" \
        "2" "vi" 2>${ANSWER} || return 1
        case $(cat ${ANSWER}) in
            "1") EDITOR="nano" ;;
            "2") EDITOR="vi" ;;
        esac
    fi
}

# set device name scheme
set_device_name_scheme() {
    NAME_SCHEME_PARAMETER=""
    NAME_SCHEME_LEVELS="FSUUID /dev/disk/by-uuid/<uuid> FSLABEL /dev/disk/by-label/<label> KERNEL /dev/<kernelname>"
    DIALOG --menu $"Select the device name scheme you want to use in config files (recommended is UUID)." 11 50 5 ${NAME_SCHEME_LEVELS} 2>${ANSWER} || return 1
    NAME_SCHEME_PARAMETER=$(cat ${ANSWER})
    NAME_SCHEME_PARAMETER_RUN="1"
}

# set GUID (gpt) usage
set_guid() {
    ## Lenono BIOS-GPT issues - Arch Forum - https://bbs.archlinux.org/viewtopic.php?id=131149 , https://bbs.archlinux.org/viewtopic.php?id=133330 , https://bbs.archlinux.org/viewtopic.php?id=138958
    ## Lenono BIOS-GPT issues - in Fedora - https://bugzilla.redhat.com/show_bug.cgi?id=735733, https://bugzilla.redhat.com/show_bug.cgi?id=749325 , http://git.fedorahosted.org/git/?p=anaconda.git;a=commit;h=ae74cebff312327ce2d9b5ac3be5dbe22e791f09
    GUIDPARAMETER=""
    DIALOG --defaultno --yesno $"Do you want to use GUID Partition Table (GPT)?\n\nIt is a standard for the layout of the partition table on a physical hard disk. Although it forms a part of the Unified Extensible Firmware Interface (UEFI) standard (replacement for the PC BIOS firmware), it is also used on some BIOS systems because of the limitations of MBR aka msdos partition tables, which restrict maximum disk size to 2 TiB.\n\nWindows XP and earlier Windows systems cannot (without hacks) read or write to drives formatted with a GUID partition table, however, Vista and Windows 7 and later versions include the capability to use GPT for non-boot aka data disks (only UEFI systems can boot Windows from GPT disks).\n\nAttention:\n- Please check if your other operating systems have GPT support!\n- Use this option for a GRUB(2) setup, which should support LVM, RAID etc.,\n  which doesn't fit into the usual 30k MS-DOS post-MBR gap.\n- BIOS-GPT boot may not work in some Lenovo systems (irrespective of the\n 
  bootloader used). " 0 0 && GUIDPARAMETER="yes"
}

# Get a list of available disks for use in the "Available disks" dialogs. This
# will print the mountpoints as follows, getting size info from /sys:
#   /dev/sda: 64000 MB
#   /dev/sdb: 64000 MB
_getavaildisks()
{
    for i in $(finddisks); do
            if [[ "$(echo "${i}" | grep '/dev/mapper')" ]]; then
                # device mapper is always 512 aligned!
                # only dmraid device can be here
                echo -n "${i} : "; echo $(($(expr 512 '*' $(dmsetup status ${i} | cut -f2 -d " "))/1000000)) MB; echo "\n"
            # special block devices
            elif [[  "$(echo "${i}" | grep "/dev/rd")" ]]; then
                echo -n "${i}: "; echo $(($(expr $(cat ${block}/rd\!$(basename ${i} | sed -e 's#p.*##g')/queue/logical_block_size) '*' $(cat ${block}/rd\!$(basename ${i} | sed -e 's#p.*##g')/size))/1000000)) MB; echo "\n"
            elif [[  "$(echo "${i}" | grep "/dev/cciss")" ]]; then
                echo -n "${i}: "; echo $(($(expr $(cat ${block}/cciss\!$(basename ${i} | sed -e 's#p.*##g')/queue/logical_block_size) '*' $(cat ${block}/cciss\!$(basename ${i} | sed -e 's#p.*##g')/size))/1000000)) MB; echo "\n"
            elif [[  "$(echo "${i}" | grep "/dev/ida")" ]]; then
                echo -n "${i}: "; echo $(($(expr $(cat ${block}/ida\!$(basename ${i} | sed -e 's#p.*##g')/queue/logical_block_size) '*' $(cat ${block}/ida\!$(basename ${i} | sed -e 's#p.*##g')/size))/1000000)) MB; echo "\n"
            else
                echo -n "${i} : "; echo $(($(expr $(cat ${block}/$(basename ${i})/queue/logical_block_size) '*' $(cat ${block}/$(basename ${i})/size))/1000000)) MB; echo "\n"
            fi
    done
}

# Get a list of available partitions for use in the "Available Mountpoints" dialogs. This
# will print the mountpoints as follows, getting size info from /sys:
#   /dev/sda1: 640 MB
#   /dev/sdb2: 640 MB
_getavailpartitions()
{
    for i in $(findpartitions); do
        # mmc and raid partitions
        if [[ "$(echo "${i}" | grep '/dev/md_d[0-9]')"  ||  "$(echo "${i}" | grep '/dev/md[0-9]p')" || "$(echo "${i}" | grep '/dev/mmcblk')" ]]; then
            echo -n "${i}: "; echo $(($(expr $(cat ${block}/$(basename ${i} | sed -e 's#p.*##g')/queue/logical_block_size) '*' $(cat ${block}/$(basename ${i} | sed -e 's#p.*##g')/$(basename ${i})/size))/1000000)) MB; echo "\n"
        # special block devices
        elif [[  "$(echo "${i}" | grep "/dev/rd")" ]]; then
                echo -n "${i}: "; echo $(($(expr $(cat ${block}/rd\!$(basename ${i} | sed -e 's#p.*##g')/queue/logical_block_size) '*' $(cat ${block}/rd\!$(basename ${i} | sed -e 's#p.*##g')/rd\!$(basename ${i})/size))/1000000)) MB; echo "\n"
        elif [[  "$(echo "${i}" | grep "/dev/cciss")" ]]; then
                echo -n "${i}: "; echo $(($(expr $(cat ${block}/cciss\!$(basename ${i} | sed -e 's#p.*##g')/queue/logical_block_size) '*' $(cat ${block}/cciss\!$(basename ${i} | sed -e 's#p.*##g')/cciss\!$(basename ${i})/size))/1000000)) MB; echo "\n"
        elif [[  "$(echo "${i}" | grep "/dev/ida")" ]]; then
                echo -n "${i}: "; echo $(($(expr $(cat ${block}/ida\!$(basename ${i} | sed -e 's#p.*##g')/queue/logical_block_size) '*' $(cat ${block}/ida\!$(basename ${i} | sed -e 's#p.*##g')/ida\!$(basename ${i})/size))/1000000)) MB; echo "\n"
        # raid device
        elif [[ "$(echo "${i}" | grep -v 'p' |grep '/dev/md')" ]]; then
            echo -n "${i}: "; echo $(($(expr $(cat ${block}/$(basename ${i})/queue/logical_block_size) '*' $(cat ${block}/$(basename ${i})/size))/1000000)) MB; echo "\n"
        # mapper devices
        elif [[ "$(echo "${i}" | grep '/dev/mapper')" ]]; then
            # mapper devices are always 512 aligned
            # crypt device
            if [[ "$(cryptsetup status ${i} 2>/dev/null)" ]]; then
                echo -n "${i}: "; echo $(($(expr 512 '*' $(cryptsetup status $(basename ${i}) | grep " size:" | sed -e 's#sectors##g' -e 's#size:##g'))/1000000)) MB; echo "\n"
            # dmraid device
            elif [[ "$(dmsetup info ${i} | grep 'DMRAID')"  ]]; then
                [[ "$(echo ${i} | grep 'p*[0-9]$')" ]] && echo -n "${i}: "; echo $(($(expr 512 '*' $(dmsetup status ${i} | cut -f2 -d " "))/1000000)) MB; echo "\n"
            # mapper device
            else
                echo -n "${i}: "; echo $(lvs -o lv_size --noheading --units m ${i} | sed -e 's#m##g') MB; echo "\n"
            fi
        else
            echo -n "${i}: "; echo $(($(expr $(cat ${block}/$(basename ${i} | sed -e 's#[0-9].*##g')/queue/logical_block_size) '*' $(cat ${block}/$(basename ${i} | sed -e 's#[0-9].*##g')/$(basename ${i})/size))/1000000)) MB; echo "\n"
        fi
    done
}

# Disable swap and all mounted partitions for the destination system. Unmount
# the destination root partition last!
_umountall()
{
    DIALOG --infobox $"Disabling swapspace, unmounting already mounted disk devices..." 0 0
    swapoff -a >/dev/null 2>&1
    umount $(mount | grep -v "${DESTDIR} " | grep "${DESTDIR}" | sed 's|\ .*||g') >/dev/null 2>&1
    umount $(mount | grep "${DESTDIR} " | sed 's|\ .*||g') >/dev/null 2>&1
}

# Disable all software raid devices
_stopmd()
{
    if [[ "$(cat /proc/mdstat 2>/dev/null | grep ^md)" ]]; then
        DISABLEMD=""
        DIALOG --defaultno --yesno $"Setup detected already running raid devices, do you want to disable them completely?" 0 0 && DISABLEMD="1"
        if [[ "${DISABLEMD}" = "1" ]]; then
            DIALOG --infobox $"Disabling all software raid devices..." 0 0
            for i in $(cat /proc/mdstat 2>/dev/null | grep ^md | sed -e 's# :.*##g'); do
                mdadm --manage --stop /dev/${i} > ${LOG}
            done
            DIALOG --infobox $"Cleaning superblocks of all software raid devices..." 0 0
            for i in $(${_BLKID} | grep "TYPE=\"linux_raid_member\"" | sed -e 's#:.*##g'); do
                mdadm --zero-superblock ${i} > ${LOG}
            done
        fi
    fi
    DISABLEMDSB=""
    if [[ "$(${_BLKID} | grep "TYPE=\"linux_raid_member\"")" ]]; then
        DIALOG --defaultno --yesno $"Setup detected superblock of raid devices, do you want to clean the superblock of them?" 0 0 && DISABLEMDSB="1"
        if [[ "${DISABLEMDSB}" = "1" ]]; then
            DIALOG --infobox $"Cleaning superblocks of all software raid devices..." 0 0
            for i in $(${_BLKID} | grep "TYPE=\"linux_raid_member\"" | sed -e 's#:.*##g'); do
                mdadm --zero-superblock ${i} > ${LOG}
            done
        fi
    fi
}

# Disable all lvm devices
_stoplvm()
{
    DISABLELVM=""
    DETECTED_LVM=""
    LV_VOLUMES="$(lvs -o vg_name,lv_name --noheading --separator - 2>/dev/null)"
    LV_GROUPS="$(vgs -o vg_name --noheading 2>/dev/null)"
    LV_PHYSICAL="$(pvs -o pv_name --noheading 2>/dev/null)"
    ! [[ "${LV_VOLUMES}" = "" ]] && DETECTED_LVM=1
    ! [[ "${LV_GROUPS}" = "" ]] && DETECTED_LVM=1
    ! [[ "${LV_PHYSICAL}" = "" ]] && DETECTED_LVM=1
    if [[ "${DETECTED_LVM}" = "1" ]]; then
        DIALOG --defaultno --yesno $"Setup detected lvm volumes, volume groups or physical devices, do you want to remove them completely?" 0 0 && DISABLELVM="1"
    fi
    if [[ "${DISABLELVM}" = "1" ]]; then
        DIALOG --infobox $"Removing logical volumes ..." 0 0
        for i in ${LV_VOLUMES}; do
            lvremove -f /dev/mapper/${i} 2>/dev/null> ${LOG}
        done
        DIALOG --infobox $"Removing logical groups ..." 0 0
        for i in ${LV_GROUPS}; do
            vgremove -f ${i} 2>/dev/null > ${LOG}
        done
        DIALOG --infobox $"Removing physical volumes ..." 0 0
        for i in ${LV_PHYSICAL}; do
            pvremove -f ${i} 2>/dev/null > ${LOG}
        done
    fi
}

# Disable all luks encrypted devices
_stopluks()
{
    DISABLELUKS=""
    DETECTED_LUKS=""
    LUKSDEVICE=""

    # detect already running luks devices
    LUKS_DEVICES="$(ls /dev/mapper/ | grep -v control)"
    for i in ${LUKS_DEVICES}; do
        cryptsetup status ${i} 2>/dev/null && LUKSDEVICE="${LUKSDEVICE} ${i}"
    done
    ! [[ "${LUKSDEVICE}" = "" ]] && DETECTED_LUKS=1
    if [[ "${DETECTED_LUKS}" = "1" ]]; then
        DIALOG --defaultno --yesno $"Setup detected running luks encrypted devices, do you want to remove them completely?" 0 0 && DISABLELUKS="1"
    fi
    if [[ "${DISABLELUKS}" = "1" ]]; then
        DIALOG --infobox $"Removing luks encrypted devices ..." 0 0
        for i in ${LUKSDEVICE}; do
            LUKS_REAL_DEVICE="$(echo $(cryptsetup status ${i} | grep device: | sed -e 's#device:##g'))"
            cryptsetup remove ${i} > ${LOG}
            # delete header from device
            dd if=/dev/zero of=${LUKS_REAL_DEVICE} bs=512 count=2048 >/dev/null 2>&1
        done
    fi
    
    DISABLELUKS=""
    DETECTED_LUKS=""

    # detect not running luks devices
    [[ "$(${_BLKID} | grep "TYPE=\"crypto_LUKS\"")" ]] && DETECTED_LUKS=1
    if [[ "${DETECTED_LUKS}" = "1" ]]; then
        DIALOG --defaultno --yesno $"Setup detected not running luks encrypted devices, do you want to remove them completely?" 0 0 && DISABLELUKS="1"
    fi
    if [[ "${DISABLELUKS}" = "1" ]]; then
        DIALOG --infobox $"Removing not running luks encrypted devices ..." 0 0
        for i in $(${_BLKID} | grep "TYPE=\"crypto_LUKS\"" | sed -e 's#:.*##g'); do
            # delete header from device
            dd if=/dev/zero of=${i} bs=512 count=2048 >/dev/null 2>&1
        done
    fi
    [[ -e /tmp/.crypttab ]] && rm /tmp/.crypttab
}

#_dmraid_update
_dmraid_update()
{
    DIALOG --infobox $"Deactivating dmraid devices ..." 0 0
    dmraid -an >/dev/null 2>&1
    if [[ "${DETECTED_LVM}" = "1" || "${DETECTED_LUKS}" = "1" ]]; then
        DIALOG --defaultno --yesno $"Setup detected running dmraid devices and/or running lvm2, luks encrypted devices. If you reduced/deleted partitions on your dmraid device a complete reset of devicemapper devices is needed. This will reset also your created lvm2 or encrypted devices. Are you sure you want to do this?" 0 0 && RESETDM="1"
        if [[ "${RESETDM}" = "1" ]]; then
            DIALOG --infobox $"Resetting devicemapper devices ..." 0 0
            dmsetup remove_all >/dev/null 2>&1
        fi
    else
        DIALOG --infobox $"Resetting devicemapper devices ..." 0 0
        dmsetup remove_all >/dev/null 2>&1
    fi
    DIALOG --infobox $"Reactivating dmraid devices ..." 0 0
    dmraid -ay -Z >/dev/null 2>&1
}

#helpbox for raid
_helpraid()
{
DIALOG --msgbox $"LINUX SOFTWARE RAID SUMMARY:\n
-----------------------------\n\n
Linear mode:\n
You have two or more partitions which are not necessarily the same size\n
(but of course can be), which you want to append to each other.\n
Spare-disks are not supported here. If a disk dies, the array dies with\n
it.\n\n
RAID-0:\n
You have two or more devices, of approximately the same size, and you want\n
to combine their storage capacity and also combine their performance by\n
accessing them in parallel. Like in Linear mode, spare disks are not\n
supported here either. RAID-0 has no redundancy, so when a disk dies, the\n
array goes with it.\n\n
RAID-1:\n
You have two devices of approximately same size, and you want the two to\n
be mirrors of each other. Eventually you have more devices, which you\n
want to keep as stand-by spare-disks, that will automatically become a\n
part of the mirror if one of the active devices break.\n\n
RAID-4:\n
You have three or more devices of roughly the same size and you want\n
a way that protects data against loss of any one disk.\n
Fault tolerance is achieved by adding an extra disk to the array, which\n
is dedicated to storing parity information. The overall capacity of the\n
array is reduced by one disk.\n
The storage efficiency is 66 percent. With six drives, the storage\n
efficiency is 87 percent. The main disadvantage is poor performance for\n
multiple,\ simultaneous, and independent read/write operations.\n
Thus, if any disk fails, all data stay intact. But if two disks fail,\n
all data is lost.\n\n
RAID-5:\n
You have three or more devices of roughly the same size, you want to\n
combine them into a larger device, but still to maintain a degree of\n
redundancy fordata safety. Eventually you have a number of devices to use\n
as spare-disks, that will not take part in the array before another device\n
fails. If you use N devices where the smallest has size S, the size of the\n
entire array will be (N-1)*S. This \"missing\" space is used for parity\n
(redundancy) information. Thus, if any disk fails, all data stay intact.\n
But if two disks fail, all data is lost.\n\n
RAID-6:\n
You have four or more devices of roughly the same size and you want\n
a way that protects data against loss of any two disks.\n
Fault tolerance is achieved by adding an two extra disk to the array,\n
which is dedicated to storing parity information. The overall capacity\n
of the array is reduced by 2 disks.\n
Thus, if any two disks fail, all data stay intact. But if 3 disks fail,\n
all data is lost.\n\n
RAID-10:\n
Shorthand for RAID1+0, a mirrored striped array and needs a minimum of\n
two disks. It provides superior data security and can survive multiple\n
disk failures. The main disadvantage is cost, because 50% of your\n
storage is duplication." 0 0
}

# Create raid or raid_partition
_raid()
{
    MDFINISH=""
    while [[ "${MDFINISH}" != "DONE" ]]; do
        activate_special_devices
        : >/tmp/.raid
        : >/tmp/.raid-spare
        # check for devices
        PARTS="$(findpartitions _)"
        ALREADYINUSE=""
        #hell yeah, this is complicated! kill software raid devices already in use.
        ALREADYINUSE=$(cat /proc/mdstat 2>/dev/null | grep ^md | sed -e 's# :.*linear##g' -e 's# :.*raid[0-9][0-9]##g' -e 's# :.*raid[0-9]##g' -e 's#\[[0-9]\]##g')
        for i in ${ALREADYINUSE}; do
            PARTS=$(echo ${PARTS} | sed -e "s#/dev/${i}\ _##g" -e "s#/dev/${i}\p[0-9]\ _##g")
            k=$(echo /dev/${i} | sed -e 's#[0-9]##g')
            if ! [[ "$(echo ${k} | grep ^md)" ]]; then
                PARTS=$(echo ${PARTS} | sed -e "s#${k}\ _##g")
            fi
        done
        # skip encrypted mapper devices which contain raid devices
        ALREADYINUSE=""
        for i in $(ls /dev/mapper/* 2>/dev/null | grep -v control); do
            cryptsetup status ${i} 2>/dev/null | grep -q "device:.*/dev/md" && ALREADYINUSE="${ALREADYINUSE} ${i}"
        done
        # skip lvm with raid devices
        for devpath in $(pvs -o pv_name --noheading); do
            # skip simple lvm device with raid device
            if [[ "$(echo ${devpath} | grep /dev/md)" ]]; then
                killvolumegroup="$(echo $(pvs -o vg_name --noheading ${devpath}))"
                ALREADYINUSE="${ALREADYINUSE} $(ls /dev/mapper/${killvolumegroup}-*)"
            fi
            # skip encrypted raid device
            if [[ "$(echo ${devpath} | grep dm-)" ]]; then
                if [[ "$(cryptsetup status $(basename ${devpath}) | grep "device:.*/dev/md")" ]]; then
                   killvolumegroup="$(echo $(pvs -o vg_name --noheading ${devpath}))"
                   ALREADYINUSE="${ALREADYINUSE} $(ls /dev/mapper/${killvolumegroup}-*)"
                fi
            fi
        done
        # skip already encrypted volume devices with raid device
        for devpath in $(ls /dev/mapper/ 2>/dev/null | grep -v control); do
            realdevice="$(cryptsetup status ${devpath} 2>/dev/null | grep "device:.*/dev/mapper/" | sed -e 's#.*\ ##g')"
            if [[ "$(lvs ${realdevice} 2>/dev/null)" ]]; then
                vg="$(echo $(lvs -o vg_name --noheading ${realdevice}))"
                if [[ "$(pvs -o pv_name,vg_name --noheading | grep "${vg}$" | grep "/dev/md")" ]]; then
                   ALREADYINUSE="${ALREADYINUSE} /dev/mapper/${devpath}"
                fi
            fi
        done
        for i in ${ALREADYINUSE}; do
            PARTS=$(echo ${PARTS} | sed -e "s#${i}\ _##g")
        done
        # break if all devices are in use
        if [[ "${PARTS}" = "" ]]; then
            DIALOG --msgbox $"All devices in use. No more devices left for new creation." 0 0
            return 1
        fi
        # enter raid device name
        RAIDDEVICE=""
        while [[ "${RAIDDEVICE}" = "" ]]; do
            if [[ "${RAID_PARTITION}" = "" ]]; then
                DIALOG --inputbox $"Enter the node name for the raiddevice:\n/dev/md[number]\n/dev/md0\n/dev/md1\n\n" 15 65 "/dev/md0" 2>${ANSWER} || return 1
            fi
            if [[ "${RAID_PARTITION}" = "1" ]]; then
                DIALOG --inputbox $"Enter the node name for partitionable raiddevice:\n/dev/md_d[number]\n/dev/md_d0\n/dev/md_d1" 15 65 "/dev/md_d0" 2>${ANSWER} || return 1
            fi
            RAIDDEVICE=$(cat ${ANSWER})
            if [[ "$(cat /proc/mdstat 2>/dev/null | grep "^$(echo ${RAIDDEVICE} | sed -e 's#/dev/##g')")" ]]; then
                DIALOG --msgbox $"ERROR: You have defined 2 identical node names! Please enter another name." 8 65
                RAIDDEVICE=""
            fi
        done
        RAIDLEVELS="linear - raid0 - raid1 - raid4 - raid5 - raid6 - raid10 -"
        DIALOG --menu $"Select the raid level you want to use" 21 50 11 ${RAIDLEVELS} 2>${ANSWER} || return 1
        LEVEL=$(cat ${ANSWER})
        # raid5 and raid10 support parity parameter
        PARITY=""
        if [[ "${LEVEL}" = "raid5" || "${LEVEL}" = "raid6" || "${LEVEL}" = "raid10" ]]; then
            PARITYLEVELS="left-asymmetric - left-symmetric - right-asymmetric - right-symmetric -"
            DIALOG --menu $"Select the parity layout you want to use (default is left-symmetric)" 21 50 13 ${PARITYLEVELS} 2>${ANSWER} || return 1
            PARTIY=$(cat ${ANSWER})
        fi
        # show all devices with sizes
        DIALOG --msgbox $"DISKS:\n$(_getavaildisks)\n\nPARTITIONS:\n$(_getavailpartitions)" 0 0
        # select the first device to use, no missing option available!
        RAIDNUMBER=1
        DIALOG --menu $"Select device ${RAIDNUMBER}" 21 50 13 ${PARTS} 2>${ANSWER} || return 1
        PART=$(cat ${ANSWER})
        echo "${PART}" >>/tmp/.raid
        while [[ "${PART}" != "DONE" ]]; do
            RAIDNUMBER=$((${RAIDNUMBER} + 1))
            # clean loop from used partition and options
            PARTS="$(echo ${PARTS} | sed -e "s#${PART}\ _##g" -e 's#MISSING\ _##g' -e 's#SPARE\ _##g')"
            # raid0 doesn't support missing devices
            ! [[ "${LEVEL}" = "raid0" || "${LEVEL}" = "linear" ]] && MDEXTRA="MISSING _"
            # add more devices
            DIALOG --menu $"Select additional device ${RAIDNUMBER}" 21 50 13 ${PARTS} ${MDEXTRA} DONE _ 2>${ANSWER} || return 1
            PART=$(cat ${ANSWER})
            SPARE=""
            ! [[ "${LEVEL}" = "raid0" || "${LEVEL}" = "linear" ]] && DIALOG --yesno --defaultno $"Would you like to use ${PART} as spare device?" 0 0 && SPARE="1"
            [[ "${PART}" = "DONE" ]] && break
            if [[ "${PART}" = "MISSING" ]]; then
                DIALOG --yesno $"Would you like to create a degraded raid on ${RAIDDEVICE}?" 0 0 && DEGRADED="missing"
                echo "${DEGRADED}" >>/tmp/.raid
            else
                if [[ "${SPARE}" = "1" ]]; then
                    echo "${PART}" >>/tmp/.raid-spare
                else
                    echo "${PART}" >>/tmp/.raid
                fi
            fi
        done
        # final step ask if everything is ok?
        DIALOG --yesno $"Would you like to create ${RAIDDEVICE} like this?\n\nLEVEL:\n${LEVEL}\n\nDEVICES:\n$(for i in $(cat /tmp/.raid); do echo "${i}\n";done)\nSPARES:\n$(for i in $(cat /tmp/.raid-spare); do echo "${i}\n";done)" 0 0 && MDFINISH="DONE"
    done
    _createraid
}

# create raid device
_createraid()
{
    DEVICES="$(echo -n $(cat /tmp/.raid))"
    SPARES="$(echo -n $(cat /tmp/.raid-spare))"
    # combine both if spares are available, spares at the end!
    [[ -n ${SPARES} ]] && DEVICES="${DEVICES} ${SPARES}"
    # get number of devices
    RAID_DEVICES="$(cat /tmp/.raid | wc -l)"
    SPARE_DEVICES="$(cat /tmp/.raid-spare | wc -l)"
    # generate options for mdadm
    RAIDOPTIONS="--force --run --level=${LEVEL}"
    [[ "$(echo ${RAIDDEVICE} | grep /md_d[0-9])" ]] && RAIDOPTIONS="${RAIDOPTIONS} -a mdp"
    ! [[ "${RAID_DEVICES}" = "0" ]] && RAIDOPTIONS="${RAIDOPTIONS} --raid-devices=${RAID_DEVICES}"
    ! [[ "${SPARE_DEVICES}" = "0" ]] && RAIDOPTIONS="${RAIDOPTIONS} --spare-devices=${SPARE_DEVICES}"
    ! [[ "${PARITY}" = "" ]] && RAIDOPTIONS="${RAIDOPTIONS} --layout=${PARITY}"
    DIALOG --infobox $"Creating ${RAIDDEVICE}..." 0 0
    mdadm --create ${RAIDDEVICE} ${RAIDOPTIONS} ${DEVICES} >${LOG} 2>&1
    if [[ $? -gt 0 ]]; then
        DIALOG --msgbox $"Error creating ${RAIDDEVICE} (see ${LOG} for details)." 0 0
        return 1
    fi
    if [[ "$(echo ${RAIDDEVICE} | grep /md_d[0-9])" ]]; then
        # switch for mbr usage
        set_guid
        if [[ "${GUIDPARAMETER}" = "" ]]; then
            DIALOG --msgbox $"Now you'll be put into the parted program where you can partition your raiddevice to your needs." 18 70
            clear
            parted ${RAIDDEVICE} print
            parted ${RAIDDEVICE}
        else
            DISC=${RAIDDEVICE}
            RUN_CGDISK="1"
            CHECK_BIOS_BOOT_GRUB=""
            CHECK_UEFISYS_PART=""
            check_gpt
        fi
    fi
}

# help for lvm
_helplvm()
{
DIALOG --msgbox $"LOGICAL VOLUME SUMMARY:\n
-----------------------------\n\n
LVM is a Logical Volume Manager for the Linux kernel. With LVM you can\n
abstract your storage space and have \"virtual partitions\" which are easier\n
to modify.\n\nThe basic building block of LVM are:\n
- Physical volume (PV):\n
  Partition on hard disk (or even hard disk itself or loopback file) on\n
  which you can have virtual groups. It has a special header and is\n
  divided into physical extents. Think of physical volumes as big building\n
  blocks which can be used to build your hard drive.\n
- Volume group (VG):\n 
  Group of physical volumes that are used as storage volume (as one disk).\n
  They contain logical volumes. Think of volume groups as hard drives.\n 
- Logical volume(LV):\n
  A \"virtual/logical partition\" that resides in a volume group and is\n 
  composed of physical extents. Think of logical volumes as normal\n
  partitions." 0 0
}

# Creates physical volume
_createpv()
{
    PVFINISH=""
    while [[ "${PVFINISH}" != "DONE" ]]; do
        activate_special_devices
        : >/tmp/.pvs-create
        PVDEVICE=""
        PARTS="$(findpartitions _)"
        ALREADYINUSE=""
        # skip volume devices
        for i in $(ls /dev/mapper/* | grep -v control); do
            [[ "$(lvs ${i} 2>/dev/null)" ]] && ALREADYINUSE="${ALREADYINUSE} ${i}"
        done
        # skip already encrypted volume devices
        for devpath in $(ls /dev/mapper/ 2>/dev/null | grep -v control); do
            realdevice="$(cryptsetup status ${devpath} 2>/dev/null | grep "device:.*/dev/mapper/" | sed -e 's#.*\ ##g')"
            if ! [[ "${realdevice}" = "" ]]; then
                [[ "$(lvs ${realdevice} 2>/dev/null)" ]] && ALREADYINUSE="${ALREADYINUSE} /dev/mapper/${devpath}"
            fi
        done
        # skip md devices, which already have lvm devices!
        for i in ${PARTS}; do
            mdcheck="$(echo ${i} | sed -e 's#/dev/##g')"
            if ! [[ "$(find ${block}/${mdcheck}/slaves/ -name 'dm*' 2>/dev/null)" = "" ]]; then
                for k in $(find ${block}/${mdcheck}/slaves/ -name 'dm*' 2>/dev/null); do
                    # check encrypted volume
                    realdevice="$(cryptsetup status $(cat ${k}/dm/name) 2>/dev/null | grep "device:.*/dev/mapper/" | sed -e 's#.*\ ##g')"
                    [[ "$(lvs ${realdevice} 2>/dev/null)" ]] && ALREADYINUSE="${ALREADYINUSE} ${i}"
                    # check on normal lvs
                    [[ "$(lvs /dev/mapper/$(cat ${k}/dm/name) 2>/dev/null)" ]] && ALREADYINUSE="${ALREADYINUSE} ${i}"
                done
            fi
        done
        # skip md partition devices, which already have lvm devices!
        for i in ${PARTS}; do
            mdcheck="$(echo ${i} | grep /dev/md*p | sed -e 's#p.*##g' -e 's#/dev/##g')"
            if [[ "$(find ${block}/${mdcheck}/slaves/ -name 'dm*' 2>/dev/null)" != "" && "${mdcheck}" != "" ]]; then
                for k in $(find ${block}/${mdcheck}/slaves/ -name 'dm*' 2>/dev/null); do
                    # check encrypted volume
                    realdevice="$(cryptsetup status $(cat ${k}/dm/name) 2>/dev/null | grep "device:.*/dev/mapper/" | sed -e 's#.*\ ##g')"
                    [[ "$(lvs ${realdevice} 2>/dev/null)" ]] && ALREADYINUSE="${ALREADYINUSE} ${i}"
                   # check on normal lvs
                    [[ "$(lvs /dev/mapper/$(cat ${k}/dm/name) 2>/dev/null)" ]] && ALREADYINUSE="${ALREADYINUSE} ${i}"
                done
            fi
        done
        for i in ${ALREADYINUSE}; do
            PARTS=$(echo ${PARTS} | sed -e "s#${i}\ _##g")
        done
        # break if all devices are in use
        if [[ "${PARTS}" = "" ]]; then
            DIALOG --msgbox $"No devices left for physical volume creation." 0 0
            return 1
        fi
        # show all devices with sizes
        DIALOG --msgbox $"DISKS:\n$(_getavaildisks)\n\nPARTITIONS:\n$(_getavailpartitions)\n\n" 0 0
        # select the first device to use
        DEVNUMBER=1
        DIALOG --menu $"Select device number ${DEVNUMBER} for physical volume" 21 50 13 ${PARTS} 2>${ANSWER} || return 1
        PART=$(cat ${ANSWER})
        echo "${PART}" >>/tmp/.pvs-create
        while [[ "${PART}" != "DONE" ]]; do
            DEVNUMBER=$((${DEVNUMBER} + 1))
            # clean loop from used partition and options
            PARTS="$(echo ${PARTS} | sed -e "s#${PART}\ _##g")"
            # add more devices
            DIALOG --menu $"Select additional device number ${DEVNUMBER} for physical volume" 21 50 13 ${PARTS} DONE _ 2>${ANSWER} || return 1
            PART=$(cat ${ANSWER})
            [[ "${PART}" = "DONE" ]] && break
            echo "${PART}" >>/tmp/.pvs-create
        done
        # final step ask if everything is ok?
        DIALOG --yesno $"Would you like to create physical volume on devices below?\n$(cat /tmp/.pvs-create | sed -e 's#$#\\n#g')" 0 0 && PVFINISH="DONE"
    done
    DIALOG --infobox $"Creating physical volume on ${PART}..." 0 0
    PART="$(echo -n $(cat /tmp/.pvs-create))"
    pvcreate ${PART} >${LOG} 2>&1
    if [[ $? -gt 0 ]]; then
        DIALOG --msgbox $"Error creating physical volume on ${PART} (see ${LOG} for details)." 0 0
        return 1
    fi
}

#find physical volumes that are not in use
findpv()
{
    for i in $(pvs -o pv_name --noheading);do
        if [[ "$(pvs -o vg_name --noheading ${i})" = "      " ]]; then
                if [[ "$(echo ${i} | grep /dev/dm-)" ]]; then
                    for k in $(ls /dev/mapper | grep -v control); do
                        if [[ -h /dev/mapper/${k} ]]; then
                            pv="$(basename ${i})"
                            if [[ "$(readlink /dev/mapper/${k} | grep ${pv}$)" ]]; then
                                echo "${i}" | sed -e "s#/dev/dm-.*#/dev/mapper/${k}#g"
                                [[ "${1}" ]] && echo ${1}
                            fi
                        fi
                    done
                else
                    echo "${i}"
                    [[ "${1}" ]] && echo ${1}
                fi
        fi
    done
}

getavailablepv()
{
    for i in "$(pvs -o pv_name,pv_size --noheading --units m)"; do
            if [[ "$(echo ${i} | grep /dev/dm-)" ]]; then
                for k in $(ls /dev/mapper | grep -v control); do
                    if [[ -h /dev/mapper/${k} ]]; then
                        pv="$(basename ${i})"
                        if [[ "$(readlink /dev/mapper/${k} | grep ${pv}$)" ]]; then
                            echo "${i}" | sed -e "s#/dev/dm-.* #/dev/mapper/${k} #g" | sed -e 's#$#\\n#'
                        fi
                    fi
                 done
            else
                echo "${i}" | sed -e 's#$#\\n#'
            fi
    done
}

#find volume groups that are not already full in use
findvg()
{
    for dev in $(vgs -o vg_name --noheading);do
        if ! [[ "$(vgs -o vg_free --noheading --units m ${dev} | grep " 0m$")" ]]; then
            echo "${dev}"
            [[ "${1}" ]] && echo ${1}
        fi
    done
}

getavailablevg()
{
    for i in $(vgs -o vg_name,vg_free --noheading --units m); do
        if ! [[ "$(echo ${i} | grep " 0m$")" ]]; then
            echo ${i} | sed -e 's#$#\\n#'
        fi
    done
}

# Creates volume group
_createvg()
{
    VGFINISH=""
    while [[ "${VGFINISH}" != "DONE" ]]; do
        : >/tmp/.pvs
        VGDEVICE=""
        PVS=$(findpv _)
        # break if all devices are in use
        if [[ "${PVS}" = "" ]]; then
            DIALOG --msgbox $"No devices left for Volume Group creation." 0 0
            return 1
        fi
        # enter volume group name
        VGDEVICE=""
        while [[ "${VGDEVICE}" = "" ]]; do
            DIALOG --inputbox $"Enter the Volume Group name:\nfoogroup\n<yourvolumegroupname>\n\n" 15 65 "foogroup" 2>${ANSWER} || return 1
            VGDEVICE=$(cat ${ANSWER})
            if [[ "$(vgs -o vg_name --noheading 2>/dev/null | grep "^  $(echo ${VGDEVICE})")" ]]; then
                DIALOG --msgbox $"ERROR: You have defined 2 identical Volume Group names! Please enter another name." 8 65
                VGDEVICE=""
            fi
        done
        # show all devices with sizes
        DIALOG --msgbox $"Physical Volumes:\n$(getavailablepv)\n\nPhysical Volumes that are not shown in next dialog, are already in use!" 0 0
        # select the first device to use, no missing option available!
        PVNUMBER=1
        DIALOG --menu $"Select Physical Volume ${PVNUMBER} for ${VGDEVICE}" 21 50 13 ${PVS} 2>${ANSWER} || return 1
        PV=$(cat ${ANSWER})
        echo "${PV}" >>/tmp/.pvs
        while [[ "${PVS}" != "DONE" ]]; do
            PVNUMBER=$((${PVNUMBER} + 1))
            # clean loop from used partition and options
            PVS="$(echo ${PVS} | sed -e "s#${PV}\ _##g")"
            # add more devices
            DIALOG --menu $"Select additional Physical Volume ${PVNUMBER} for ${VGDEVICE}" 21 50 13 ${PVS} DONE _ 2>${ANSWER} || return 1
            PV=$(cat ${ANSWER})
            [[ "${PV}" = "DONE" ]] && break
            echo "${PV}" >>/tmp/.pvs
        done
        # final step ask if everything is ok?
        DIALOG --yesno $"Would you like to create Volume Group like this?\n\n${VGDEVICE}\n\nPhysical Volumes:\n$(cat /tmp/.pvs | sed -e 's#$#\\n#g')" 0 0 && VGFINISH="DONE"
    done
    DIALOG --infobox $"Creating Volume Group ${VGDEVICE}..." 0 0
    PV="$(echo -n $(cat /tmp/.pvs))"
    vgcreate ${VGDEVICE} ${PV} >${LOG} 2>&1
    if [[ $? -gt 0 ]]; then
        DIALOG --msgbox $"Error creating Volume Group ${VGDEVICE} (see ${LOG} for details)." 0 0
        return 1
    fi
}

# Creates logical volume
_createlv()
{
    LVFINISH=""
    while [[ "${LVFINISH}" != "DONE" ]]; do
        LVDEVICE=""
        LV_SIZE_SET=""
        LVS=$(findvg _)
        # break if all devices are in use
        if [[ "${LVS}" = "" ]]; then
            DIALOG --msgbox $"No Volume Groups with free space available for Logical Volume creation." 0 0
            return 1
        fi
        # show all devices with sizes
        DIALOG --msgbox $"Volume Groups:\n$(getavailablevg)\n\nVolume Groups that are not shown, are already 100% in use!" 0 0
        DIALOG --menu $"Select Volume Group" 21 50 13 ${LVS} 2>${ANSWER} || return 1
        LV=$(cat ${ANSWER})
        # enter logical volume name
        LVDEVICE=""
        while [[ "${LVDEVICE}" = "" ]]; do
            DIALOG --inputbox $"Enter the Logical Volume name:\nfooname\n<yourvolumename>\n\n" 15 65 "fooname" 2>${ANSWER} || return 1
            LVDEVICE=$(cat ${ANSWER})
            if [[ "$(lvs -o lv_name,vg_name --noheading 2>/dev/null | grep " $(echo ${LVDEVICE}) $(echo ${LV})"$)" ]]; then
                DIALOG --msgbox $"ERROR: You have defined 2 identical Logical Volume names! Please enter another name." 8 65
                LVDEVICE=""
            fi
        done
        while [[ "${LV_SIZE_SET}" = "" ]]; do
            LV_ALL=""
            DIALOG --inputbox $"Enter the size (MB) of your Logical Volume,\nMinimum value is > 0.\n\nVolume space left: $(vgs -o vg_free --noheading --units m ${LV})B\n\nIf you enter no value, all free space left will be used." 16 65 "" 2>${ANSWER} || return 1
                LV_SIZE=$(cat ${ANSWER})
                if [[ "${LV_SIZE}" = "" ]]; then
                    DIALOG --yesno $"Would you like to create Logical Volume with no free space left?" 0 0 && LV_ALL="1"
                    if ! [[ "${LV_ALL}" = "1" ]]; then
                         LV_SIZE=0
                    fi
                fi
                if [[ "${LV_SIZE}" = "0" ]]; then
                    DIALOG --msgbox $"ERROR: You have entered a invalid size, please enter again." 0 0
                else
                    if [[ "${LV_SIZE}" -ge "$(vgs -o vg_free --noheading --units m | sed -e 's#m##g')" ]]; then
                        DIALOG --msgbox $"ERROR: You have entered a too large size, please enter again." 0 0
                    else
                        LV_SIZE_SET=1
                    fi
                fi
        done
        #Contiguous doesn't work with +100%FREE
        LV_CONTIGUOUS=""
        [[ "${LV_ALL}" = "" ]] && DIALOG --defaultno --yesno $"Would you like to create Logical Volume as a contiguous partition, that means that your space doesn't get partitioned over one or more disks nor over non-contiguous physical extents.\n(usefull for swap space etc.)?" 0 0 && LV_CONTIGUOUS="1"
        if [[ "${LV_CONTIGUOUS}" = "1" ]]; then
            CONTIGUOUS=yes
            LV_EXTRA="-C y"
        else
            CONTIGUOUS=no
            LV_EXTRA=""
        fi
        [[ "${LV_SIZE}" = "" ]] && LV_SIZE="All free space left"
        # final step ask if everything is ok?
        DIALOG --yesno $"Would you like to create Logical Volume ${LVDEVICE} like this?\nVolume Group:\n${LV}\nVolume Size:\n${LV_SIZE}\nContiguous Volume:\n${CONTIGUOUS}" 0 0 && LVFINISH="DONE"
    done
    DIALOG --infobox $"Creating Logical Volume ${LVDEVICE}..." 0 0
    if [[ "${LV_ALL}" = "1" ]]; then
        lvcreate ${LV_EXTRA} -l +100%FREE ${LV} -n ${LVDEVICE} >${LOG} 2>&1
    else
        lvcreate ${LV_EXTRA} -L ${LV_SIZE} ${LV} -n ${LVDEVICE} >${LOG} 2>&1
    fi
    if [[ $? -gt 0 ]]; then
        DIALOG --msgbox $"Error creating Logical Volume ${LVDEVICE} (see ${LOG} for details)." 0 0
        return 1
    fi
}

# enter luks name
_enter_luks_name() {
    LUKSDEVICE=""
    while [[ "${LUKSDEVICE}" = "" ]]; do
        DIALOG --inputbox $"Enter the name for luks encrypted device ${PART}:\nfooname\n<yourname>\n\n" 15 65 "fooname" 2>${ANSWER} || return 1
        LUKSDEVICE=$(cat ${ANSWER})
        if ! [[ "$(cryptsetup status ${LUKSDEVICE} | grep inactive)" ]]; then
            DIALOG --msgbox $"ERROR: You have defined 2 identical luks encryption device names! Please enter another name." 8 65
            LUKSDEVICE=""
        fi
    done
}

# enter luks passphrase
_enter_luks_passphrase () {
    LUKSPASSPHRASE=""
    while [[ "${LUKSPASSPHRASE}" = "" ]]; do
        DIALOG --insecure --passwordbox $"Enter passphrase for luks encrypted device ${PART}:" 0 0 2>${ANSWER} || return 1
        LUKSPASS=$(cat ${ANSWER})
        DIALOG --insecure --passwordbox $"Retype passphrase for luks encrypted device ${PART}:" 0 0 2>${ANSWER} || return 1
        LUKSPASS2=$(cat ${ANSWER})
        if [[ "${LUKSPASS}" = "${LUKSPASS2}" ]]; then
            LUKSPASSPHRASE=${LUKSPASS}
            echo ${LUKSPASSPHRASE} > /tmp/.passphrase
            LUKSPASSPHRASE=/tmp/.passphrase
        else
             DIALOG --msgbox $"Passphrases didn't match, please enter again." 0 0
        fi
    done
}

# opening luks
_opening_luks() {
    DIALOG --infobox $"Opening encrypted ${PART}..." 0 0
    luksOpen_success="0"
    while [[ "${luksOpen_success}" = "0" ]]; do
        cryptsetup luksOpen ${PART} ${LUKSDEVICE} >${LOG} <${LUKSPASSPHRASE} && luksOpen_success=1
        if [[ "${luksOpen_success}" = "0" ]]; then
            DIALOG --msgbox $"Error: Passphrases didn't match, please enter again." 0 0
            _enter_luks_passphrase || return 1
        fi
    done
    LUKSPASSPHRASE="$(cat ${LUKSPASSPHRASE})"
    DIALOG --yesno $"Would you like to save the passphrase of luks device in /etc/crypttab?\nName:${LUKSDEVICE}" 0 0 || LUKSPASSPHRASE="ASK"
    echo ${LUKSDEVICE} ${PART} ${LUKSPASSPHRASE} >> /tmp/.crypttab
    [[ -e /tmp/.passphrase ]] && rm /tmp/.passphrase
}

# help for luks
_helpluks()
{
DIALOG --msgbox $"LUKS ENCRYPTION SUMMARY:\n
-----------------------------\n\n
Encryption is useful for two (related) reasons.\n
Firstly, it prevents anyone with physical access to your computer,\n
and your hard drive in particular, from getting the data from it\n
(unless they have your passphrase/key).\n
Secondly, it allows you to wipe the data on your hard drive with\n
far more confidence in the event of you selling or discarding\n
your drive.\n
Basically, it supplements the access control mechanisms of the operating\n
system (like file permissions) by making it harder to bypass the operating\n
system by inserting a boot CD, for example. Encrypting the root partition\n
prevents anyone from using this method to insert viruses or trojans onto\n
your computer.\n\n
ATTENTION:\n
Having encrypted partitions does not protect you from all possible\n
attacks. The encryption is only as good as your key management, and there\n
are other ways to break into computers, while they are running." 0 0
}

# create luks device
_luks()
{
    NAME_SCHEME_PARAMETER_RUN=""
    LUKSFINISH=""
    while [[ "${LUKSFINISH}" != "DONE" ]]; do
        activate_special_devices
        PARTS="$(findpartitions _)"
        ALREADYINUSE=""
        # skip already encrypted devices, device mapper!
        for devpath in $(ls /dev/mapper 2>/dev/null | grep -v control); do
            [[ "$(cryptsetup status ${devpath})" ]] && ALREADYINUSE="${ALREADYINUSE} /dev/mapper/${devpath}"
        done
        # skip already encrypted devices, device mapper with encrypted parts!
        for devpath in $(pvs -o pv_name --noheading); do
             if [[ "$(echo ${devpath} | grep dm-)" ]]; then
                if [[ "$(cryptsetup status $(basename ${devpath}))" ]]; then
                   killvolumegroup="$(echo $(pvs -o vg_name --noheading ${devpath}))"
                   ALREADYINUSE="${ALREADYINUSE} $(ls /dev/mapper/${killvolumegroup}-*)"
                fi
             fi
             # remove hidden crypt by md device
             if [[ "$(echo ${devpath} | grep /dev/md)" ]]; then
                 mdcheck="$(echo ${devpath} | sed -e 's#/dev/##g')"
                 if ! [[ "$(find ${block}/${mdcheck}/slaves/ -name 'dm*' 2>/dev/null)" = "" ]]; then
                     for k in $(find ${block}/${mdcheck}/slaves/ -name 'dm*'); do
                         if [[ "$(cryptsetup status $(cat ${k}/dm/name))" ]]; then
                             killvolumegroup="$(echo $(pvs -o vg_name --noheading ${devpath}))"
                             ALREADYINUSE="${ALREADYINUSE} $(ls /dev/mapper/${killvolumegroup}-*)"
                         fi
                     done
                 fi
             fi
        done
        # skip md devices, which already has encrypted devices!
        for i in ${PARTS}; do
            mdcheck="$(echo ${i} | sed -e 's#/dev/##g')"
            if ! [[ "$(find ${block}/${mdcheck}/slaves/ -name 'dm*' 2>/dev/null)" = "" ]]; then
                for k in $(find ${block}/${mdcheck}/slaves/ -name 'dm*' 2>/dev/null); do
                    [[ "$(cryptsetup status $(cat ${k}/dm/name))"  ]] && ALREADYINUSE="${ALREADYINUSE} ${i}"
                    # check lvm devices if encryption was used!
                    if [[ "$(lvs /dev/mapper/$(cat ${k}/dm/name) 2>/dev/null)" ]]; then
                        for devpath in ${ALREADYINUSE}; do
                            [[ "$(echo ${devpath} | grep "/dev/mapper/$(cat ${k}/dm/name)"$)" ]] && ALREADYINUSE="${ALREADYINUSE} ${i}"
                        done
                    fi
                done
            fi
        done
        # skip md partition devices, which already has encrypted devices!
        for i in ${PARTS}; do
            mdcheck="$(echo ${i} | grep /dev/md*p | sed -e 's#p.*##g' -e 's#/dev/##g')"
            if [[ "$(find ${block}/${mdcheck}/slaves/ -name 'dm*' 2>/dev/null)" != "" && "${mdcheck}" != "" ]]; then
                for k in $(find ${block}/${mdcheck}/slaves/ -name 'dm*' 2>/dev/null); do
                    [[ "$(cryptsetup status $(cat ${k}/dm/name))" ]] && ALREADYINUSE="${ALREADYINUSE} ${i}"
                    # check lvm devices if encryption was used!
                    if [[ "$(lvs /dev/mapper/$(cat ${k}/dm/name) 2>/dev/null)" ]]; then
                        for devpath in ${ALREADYINUSE}; do
                            [[ "$(echo ${devpath} | grep "/dev/mapper/$(cat ${k}/dm/name)"$)" ]] && ALREADYINUSE="${ALREADYINUSE} ${i}"
                        done
                    fi
                done
            fi
        done
        for i in ${ALREADYINUSE}; do
            PARTS=$(echo ${PARTS} | sed -e "s#${i}\ _##g")
        done
        # break if all devices are in use
        if [[ "${PARTS}" = "" ]]; then
            DIALOG --msgbox $"No devices left for luks encryption." 0 0
            return 1
        fi
        # show all devices with sizes
        DIALOG --msgbox $"DISKS:\n$(_getavaildisks)\n\nPARTITIONS:\n$(_getavailpartitions)\n\n" 0 0
        DIALOG --menu $"Select device for luks encryption" 21 50 13 ${PARTS} 2>${ANSWER} || return 1
        PART=$(cat ${ANSWER})
        # enter luks name
        _enter_luks_name
        ### TODO: offer more options for encrypt!
        # final step ask if everything is ok?
        DIALOG --yesno $"Would you like to encrypt luks device below?\nName:${LUKSDEVICE}\nDevice:${PART}\n" 0 0 && LUKSFINISH="DONE"
    done
    _enter_luks_passphrase
    DIALOG --infobox $"Encrypting ${PART}..." 0 0
    cryptsetup -c aes-cbc-essiv:sha256 -s 128 luksFormat ${PART} >${LOG} <${LUKSPASSPHRASE}
    _opening_luks
}

autoprepare() {
    # check on encrypted devices, else weird things can happen!
    _stopluks
    # check on raid devices, else weird things can happen during partitioning!
    _stopmd
    # check on lvm devices, else weird things can happen during partitioning!
    _stoplvm
    NAME_SCHEME_PARAMETER_RUN=""
    # switch for mbr usage
    set_guid
    DISCS=$(default_blockdevices)
    if [[ "$(echo ${DISCS} | wc -w)" -gt 1 ]]; then
        DIALOG --msgbox $"Available Disks:\n\n$(_getavaildisks)\n" 0 0
        DIALOG --menu $"Select the hard drive to use" 14 55 7 $(default_blockdevices _) 2>${ANSWER} || return 1
        DISC=$(cat ${ANSWER})
    else
        DISC=${DISCS}
    fi
    DEFAULTFS=""
    BOOT_PART_SET=""
    SWAP_PART_SET=""
    ROOT_PART_SET=""
    CHOSEN_FS=""
    # get just the disk size in 1000*1000 MB
    if [[ "$(cat ${block}/$(basename ${DISC} 2>/dev/null)/size 2>/dev/null)" ]]; then
        DISC_SIZE="$(($(expr $(cat ${block}/$(basename ${DISC})/queue/logical_block_size) '*' $(cat ${block}/$(basename ${DISC})/size))/1000000))"
    else
        DIALOG --msgbox $"ERROR: Setup cannot detect size of your device, please use normal installation routine for partitioning and mounting devices." 0 0
        return 1
    fi
    while [[ "${DEFAULTFS}" = "" ]]; do
        FSOPTS=""
        [[ "$(which mkfs.ext2 2>/dev/null)" ]] && FSOPTS="${FSOPTS} ext2 Ext2"
        [[ "$(which mkfs.ext3 2>/dev/null)" ]] && FSOPTS="${FSOPTS} ext3 Ext3"
        [[ "$(which mkfs.ext4 2>/dev/null)" ]] && FSOPTS="${FSOPTS} ext4 Ext4"
        [[ "$(which mkfs.btrfs 2>/dev/null)" ]] && FSOPTS="${FSOPTS} btrfs Btrfs-(Experimental)"
        [[ "$(which mkfs.nilfs2 2>/dev/null)" ]] && FSOPTS="${FSOPTS} nilfs2 Nilfs2-(Experimental)"
        [[ "$(which mkreiserfs 2>/dev/null)" ]] && FSOPTS="${FSOPTS} reiserfs Reiser3"
        [[ "$(which mkfs.xfs 2>/dev/null)" ]] && FSOPTS="${FSOPTS} xfs XFS"
        [[ "$(which mkfs.jfs 2>/dev/null)" ]] && FSOPTS="${FSOPTS} jfs JFS"
        # create 1 MB bios_grub partition for grub-bios GPT support
        if [[ "${GUIDPARAMETER}" = "yes" ]]; then
            GUID_PART_SIZE="2"
            GPT_BIOS_GRUB_PART_SIZE="${GUID_PART_SIZE}"
            UEFISYS_PART_SIZE="512"
        else
            GUID_PART_SIZE="0"
            UEFISYS_PART_SIZE="0"
        fi
        DISC_SIZE=$((${DISC_SIZE}-${GUID_PART_SIZE}-${UEFISYS_PART_SIZE}))
        while [[ "${BOOT_PART_SET}" = "" ]]; do
            DIALOG --inputbox $"Enter the size (MB) of your /boot partition,\nMinimum value is 16.\n\nDisk space left: ${DISC_SIZE} MB" 10 65 "512" 2>${ANSWER} || return 1
            BOOT_PART_SIZE="$(cat ${ANSWER})"
            if [[ "${BOOT_PART_SIZE}" = "" ]]; then
                DIALOG --msgbox $"ERROR: You have entered a invalid size, please enter again." 0 0
            else
                if [[ "${BOOT_PART_SIZE}" -ge "${DISC_SIZE}" || "${BOOT_PART_SIZE}" -lt "16" || "${SBOOT_PART_SIZE}" = "${DISC_SIZE}" ]]; then
                    DIALOG --msgbox $"ERROR: You have entered an invalid size, please enter again." 0 0
                else
                    BOOT_PART_SET=1
                fi
            fi
        done
        DISC_SIZE=$((${DISC_SIZE}-${BOOT_PART_SIZE}))
        SWAP_SIZE="256"
        [[ "${DISC_SIZE}" -lt "256" ]] && SWAP_SIZE="${DISC_SIZE}"
        while [[ "${SWAP_PART_SET}" = "" ]]; do
            DIALOG --inputbox $"Enter the size (MB) of your swap partition,\nMinimum value is > 0.\n\nDisk space left: ${DISC_SIZE} MB" 10 65 "${SWAP_SIZE}" 2>${ANSWER} || return 1
            SWAP_PART_SIZE=$(cat ${ANSWER})
            if [[ "${SWAP_PART_SIZE}" = "" || "${SWAP_PART_SIZE}" = "0" ]]; then
                DIALOG --msgbox $"ERROR: You have entered an invalid size, please enter again." 0 0
            else
                if [[ "${SWAP_PART_SIZE}" -ge "${DISC_SIZE}" ]]; then
                    DIALOG --msgbox $"ERROR: You have entered a too large size, please enter again." 0 0
                else
                    SWAP_PART_SET=1
                fi
            fi
        done
        DISC_SIZE=$((${DISC_SIZE}-${SWAP_PART_SIZE}))
        ROOT_SIZE="7500"
        [[ "${DISC_SIZE}" -lt "7500" ]] && ROOT_SIZE="${DISC_SIZE}"
        while [[ "${ROOT_PART_SET}" = "" ]]; do
        DIALOG --inputbox $"Enter the size (MB) of your / partition,\nthe /home partition will use the remaining space.\n\nDisk space left:  ${DISC_SIZE} MB" 10 65 "${ROOT_SIZE}" 2>${ANSWER} || return 1
        ROOT_PART_SIZE=$(cat ${ANSWER})
            if [[ "${ROOT_PART_SIZE}" = "" || "${ROOT_PART_SIZE}" = "0" ]]; then
                DIALOG --msgbox $"ERROR: You have entered an invalid size, please enter again." 0 0
            else
                if [[ "${ROOT_PART_SIZE}" -ge "${DISC_SIZE}" ]]; then
                    DIALOG --msgbox $"ERROR: You have entered a too large size, please enter again." 0 0
                else
                    DIALOG --yesno $"$((${DISC_SIZE}-${ROOT_PART_SIZE})) MB will be used for your /home partition. Is this OK?" 0 0 && ROOT_PART_SET=1
                fi
            fi
        done
        while [[ "${CHOSEN_FS}" = "" ]]; do
            DIALOG --menu $"Select a filesystem for / and /home:" 16 45 8 ${FSOPTS} 2>${ANSWER} || return 1
            FSTYPE=$(cat ${ANSWER})
            DIALOG --yesno $"${FSTYPE} will be used for / and /home. Is this OK?" 0 0 && CHOSEN_FS=1
        done
        DEFAULTFS=1
    done
    DIALOG --defaultno --yesno $"${DISC} will be COMPLETELY ERASED!  Are you absolutely sure?" 0 0 \
    || return 1
    DEVICE=${DISC}

    # validate DEVICE
    if [[ ! -b "${DEVICE}" ]]; then
      DIALOG --msgbox $"Device '${DEVICE}' is not valid" 0 0
      return 1
    fi

    # validate DEST
    if [[ ! -d "${DESTDIR}" ]]; then
        DIALOG --msgbox $"Destination directory '${DESTDIR}' is not valid" 0 0
        return 1
    fi

    [[ -e /tmp/.fstab ]] && rm -f /tmp/.fstab
    # disable swap and all mounted partitions, umount / last!
    _umountall
    if [[ "${NAME_SCHEME_PARAMETER_RUN}" == "" ]]; then
        set_device_name_scheme || return 1
    fi
    # we assume a /dev/hdX format (or /dev/sdX)
    if [[ "${GUIDPARAMETER}" == "yes" ]]; then
        PART_ROOT="${DEVICE}5"
        # GPT (GUID) is supported only by 'parted' or 'sgdisk'
        printk off
        DIALOG --infobox $"Partitioning ${DEVICE}" 0 0
        # clean partition table to avoid issues!
        sgdisk --zap ${DEVICE} &>/dev/null
        # clear all magic strings/signatures - mdadm, lvm, partition tables etc.
        dd if=/dev/zero of=${DEVICE} bs=512 count=2048 &>/dev/null
        wipefs -a ${DEVICE} &>/dev/null
        # create fresh GPT
        sgdisk --clear ${DEVICE} &>/dev/null
        # create actual partitions
        sgdisk --set-alignment="2048" --new=1:1M:+${GPT_BIOS_GRUB_PART_SIZE}M --typecode=1:EF02 --change-name=1:BIOS_GRUB ${DEVICE} > ${LOG}
        sgdisk --set-alignment="2048" --new=2:0:+${UEFISYS_PART_SIZE}M --typecode=2:EF00 --change-name=2:UEFI_SYSTEM ${DEVICE} > ${LOG}
        sgdisk --set-alignment="2048" --new=3:0:+${BOOT_PART_SIZE}M --typecode=3:8300 --attributes=3:set:2 --change-name=3:CINNARCH_BOOT ${DEVICE} > ${LOG}
        sgdisk --set-alignment="2048" --new=4:0:+${SWAP_PART_SIZE}M --typecode=4:8200 --change-name=4:CINNARCH_SWAP ${DEVICE} > ${LOG}
        sgdisk --set-alignment="2048" --new=5:0:+${ROOT_PART_SIZE}M --typecode=5:8300 --change-name=5:CINNARCH_ROOT ${DEVICE} > ${LOG}
        sgdisk --set-alignment="2048" --new=6:0:0 --typecode=6:8300 --change-name=6:CINNARCH_HOME ${DEVICE} > ${LOG}
        sgdisk --print ${DEVICE} > ${LOG}
    else
        PART_ROOT="${DEVICE}3"
        # start at sector 1 for 4k drive compatibility and correct alignment
        printk off
        DIALOG --infobox $"Partitioning ${DEVICE}" 0 0
        # clean partitiontable to avoid issues!
        dd if=/dev/zero of=${DEVICE} bs=512 count=2048 >/dev/null 2>&1
        wipefs -a ${DEVICE} &>/dev/null
        # create DOS MBR with parted
        parted -a optimal -s ${DEVICE} mktable msdos >/dev/null 2>&1
        parted -a optimal -s ${DEVICE} mkpart primary 1 $((${GUID_PART_SIZE}+${BOOT_PART_SIZE})) >${LOG}
        parted -a optimal -s ${DEVICE} set 1 boot on >${LOG}
        parted -a optimal -s ${DEVICE} mkpart primary $((${GUID_PART_SIZE}+${BOOT_PART_SIZE})) $((${GUID_PART_SIZE}+${BOOT_PART_SIZE}+${SWAP_PART_SIZE})) >${LOG}
        parted -a optimal -s ${DEVICE} mkpart primary $((${GUID_PART_SIZE}+${BOOT_PART_SIZE}+${SWAP_PART_SIZE})) $((${GUID_PART_SIZE}+${BOOT_PART_SIZE}+${SWAP_PART_SIZE}+${ROOT_PART_SIZE})) >${LOG}
        parted -a optimal -s ${DEVICE} mkpart primary $((${GUID_PART_SIZE}+${BOOT_PART_SIZE}+${SWAP_PART_SIZE}+${ROOT_PART_SIZE})) 100% >${LOG}
    fi
    if [[ $? -gt 0 ]]; then
        DIALOG --msgbox $"Error partitioning ${DEVICE} (see ${LOG} for details)" 0 0
        printk on
        return 1
    fi
    printk on
    ## wait until /dev initialized correct devices
    udevadm settle

    ## FSSPECS - default filesystem specs (the + is bootable flag)
    ## <partnum>:<mountpoint>:<partsize>:<fstype>[:<fsoptions>][:+]:labelname
    ## The partitions in FSSPECS list should be listed in the "mountpoint" order.
    ## Make sure the "root" partition is defined first in the FSSPECS list
    FSSPECS="3:/:${ROOT_PART_SIZE}:${FSTYPE}:::ROOT_CINNARCH 1:/boot:${BOOT_PART_SIZE}:ext2::+:BOOT_CINNARCH 4:/home:*:${FSTYPE}:::HOME_CINNARCH 2:swap:${SWAP_PART_SIZE}:swap:::SWAP_CINNARCH"

    if [[ "${GUIDPARAMETER}" == "yes" ]]; then
        FSSPECS="5:/:${ROOT_PART_SIZE}:${FSTYPE}:::ROOT_CINNARCH 3:/boot:${BOOT_PART_SIZE}:ext2::+:BOOT_CINNARCH 2:/boot/efi:512:vfat:-F32::ESP 6:/home:*:${FSTYPE}:::HOME_CINNARCH 4:swap:${SWAP_PART_SIZE}:swap:::SWAP_CINNARCH"
    fi

    ## make and mount filesystems
    for fsspec in ${FSSPECS}; do
        part="$(echo ${fsspec} | tr -d ' ' | cut -f1 -d:)"
        mountpoint="$(echo ${fsspec} | tr -d ' ' | cut -f2 -d:)"
        fstype="$(echo ${fsspec} | tr -d ' ' | cut -f4 -d:)"
        fsoptions="$(echo ${fsspec} | tr -d ' ' | cut -f5 -d:)"
        [[ "${fsoptions}" == "" ]] && fsoptions="NONE"
        labelname="$(echo ${fsspec} | tr -d ' ' | cut -f7 -d:)"
        btrfsdevices="${DEVICE}${part}"
        btrfsssd="NONE"
        btrfscompress="NONE"
        btrfssubvolume="NONE"
        btrfslevel="NONE"
        dosubvolume="no"
        # if echo "${mountpoint}" | tr -d ' ' | grep '^/$' 2>&1 >/dev/null; then
        # if [[ "$(echo ${mountpoint} | tr -d ' ' | grep '^/$' | wc -l)" -eq 0 ]]; then
        DIALOG --infobox $"Creating ${fstype} on ${DEVICE}${part}\nwith FSLABEL ${labelname} .\nMountpoint is ${mountpoint} ." 0 0
        _mkfs yes "${DEVICE}${part}" "${fstype}" "${DESTDIR}" "${mountpoint}" "${labelname}" "${fsoptions}" "${btrfsdevices}" "${btrfssubvolume}" "${btrfslevel}" "${dosubvolume}" "${btrfssd}" "${btrfscompress}" || return 1
        # fi
    done

    DIALOG --msgbox $"Auto-prepare was successful" 0 0
    S_MKFSAUTO=1
}

check_gpt() {
    GUID_DETECTED=""
    [[ "$(${_BLKID} -p -i -o value -s PTTYPE ${DISC})" == "gpt" ]] && GUID_DETECTED="1"
    
    if [[ "${GUID_DETECTED}" == "" ]]; then
        DIALOG --defaultno --yesno $"Setup detected no GUID (gpt) partition table on ${DISC}.\n\nDo you want to convert the existing MBR table in ${DISC} to a GUID (gpt) partition table?\n\nNOTE:\nBIOS-GPT boot may not work in some Lenovo systems (irrespective of the bootloader used). " 0 0 || return 1
        sgdisk --mbrtogpt ${DISC} > ${LOG} && GUID_DETECTED="1"
    fi
    
    if [[ "${GUID_DETECTED}" == "1" ]]; then
        if [[ "${CHECK_UEFISYS_PART}" == "1" ]]; then
            check_uefisyspart
        fi
        
        if [[ "${CHECK_BIOS_BOOT_GRUB}" == "1" ]]; then
            if ! [[ "$(sgdisk -p ${DISC} | grep 'EF02')" ]]; then
                DIALOG --msgbox $"Setup detected no BIOS BOOT PARTITION in ${DISC}. Please create a >=1 MB BIOS Boot partition for grub-bios GPT support." 0 0
                RUN_CGDISK="1"
            fi
        fi
    fi
    
    if [[ "${RUN_CGDISK}" == "1" ]]; then
        DIALOG --msgbox $"Now you'll be put into cgdisk where you can partition your hard drive.\nYou should make a swap partition and as many data partitions as you will need." 18 70
        clear && cgdisk ${DISC}
    fi
}

## check and mount UEFI SYSTEM PARTITION at /boot/efi
check_uefisyspart() {
    
    if [[ "$(${_BLKID} -p -i -o value -s PTTYPE ${DISC})" != "gpt" ]]; then
        DIALOG --msgbox $"Setup detected no GUID (gpt) partition table on ${DISC}.\nUEFI boot requires ${DISC} to be partitioned as GPT.\nSetup will now try to non-destructively convert ${DISC} to GPT using sgdisk." 0 0
        sgdisk --mbrtogpt "${DISC}" > "${LOG}" && GUID_DETECTED="1"
    fi
    
    if [[ ! "$(sgdisk -p ${DISC} | grep 'EF00')" ]]; then
        DIALOG --msgbox $"Setup detected no UEFI SYSTEM PARTITION in ${DISC}. You will now be put into cgdisk. Please create a >=512 MiB partition with gdisk type code EF00 .\nWhen prompted (later) to format as FAT32, say Yes.\nIf you already have a >=512 MiB FAT32 UEFI SYSTEM Partition, check whether that partition has EF00 gdisk type code." 0 0
        clear && cgdisk "${DISC}"
        RUN_CGDISK=""
    fi
    
    if [[ "$(sgdisk -p ${DISC} | grep 'EF00')" ]]; then
        UEFISYS_PART_NUM="$(sgdisk -p ${DISC} | grep 'EF00' | tail -n +1 | awk '{print $1}')"
        UEFISYS_PART="${DISC}${UEFISYS_PART_NUM}"
        
        if [[ "$(${_BLKID} -p -i -o value -s TYPE ${UEFISYS_PART})" == "vfat" ]]; then
            if [[ "$(${_BLKID} -p -i -o value -s VERSION ${UEFISYS_PART})" != "FAT32" ]]; then
                ## Check whether UEFISYS is FAT32 (specifically), otherwise warn the user (but do not exit).
                DIALOG --defaultno --yesno $"UEFI SYSTEM PARTIION ${UEFISYS_PART} is not FAT32 formatted. Some UEFI firmwares may not work properly with a FAT16 or FAT12 filesystem in the UEFISYS partition.\nDo you want to format ${UEFISYS_PART} as FAT32?" 0 0 && _FORMAT_UEFISYS_FAT32="1"
            fi
        else
            ## Check whether UEFISYS is FAT, otherwise inform the user and offer to format the partition as FAT32.
            DIALOG --defaultno --yesno $"UEFI Specification requires UEFI SYSTEM PARTIION to be formatted as FAT32.\nDo you want to format ${UEFISYS_PART} as FAT32?" 0 0 && _FORMAT_UEFISYS_FAT32="1"
        fi
        
        umount "${DESTDIR}/boot/efi" &> /dev/null
        umount "${UEFISYS_PART}" &> /dev/null
        rm -rf "${DESTDIR}/boot/efi"
        
        if [[ "${_FORMAT_UEFISYS_FAT32}" == "1" ]]; then
            mkfs.vfat -F32 -n "ESP" "${UEFISYS_PART}"
        fi
        
        mkdir -p "${DESTDIR}/boot/efi"
        
        if [[ "$(${_BLKID} -p -i -o value -s TYPE ${UEFISYS_PART})" == "vfat" ]]; then
            mount -o rw,flush -t vfat "${UEFISYS_PART}" "${DESTDIR}/boot/efi"
        else
            DIALOG --msgbox $"${UEFISYS_PART} is not formatted using FAT filesystem. Setup will go ahead but there might be issues using non-FAT FS for UEFISYS partition." 0 0
            
            mount -o rw "${UEFISYS_PART}" "${DESTDIR}/boot/efi"
        fi
        
        ## Fix (possible) case-sensitivity issues
        if [[ -d "${DESTDIR}/boot/efi/efi" ]]; then
            mv "${DESTDIR}/boot/efi/efi" "${DESTDIR}/boot/efi/EFI_"
            mv "${DESTDIR}/boot/efi/EFI_" "${DESTDIR}/boot/efi/EFI"
        fi
        
        [[ ! -d "${DESTDIR}/boot/efi/EFI" ]] && mkdir -p "${DESTDIR}/boot/efi/EFI"
    else
        DIALOG --msgbox $"Setup did not find any UEFI SYSTEM PARTITION in ${DISC}. Please create a >=512MiB FAT32 partition with gdisk type code EFOO and try again." 0 0
        return 1
    fi
    
}

partition() {
    # disable swap and all mounted partitions, umount / last!
    _umountall
    # check on encrypted devices, else weird things can happen!
    _stopluks
    # check on raid devices, else weird things can happen during partitioning!
    _stopmd
    # check on lvm devices, else weird things can happen during partitioning!
    _stoplvm
    # update dmraid
    _dmraid_update
    # switch for mbr usage
    set_guid
    # Select disk to partition
    DISCS=$(finddisks _)
    DISCS="${DISCS} OTHER _ DONE +"
    DIALOG --msgbox $"Available Disks:\n\n$(_getavaildisks)\n" 0 0
    DISC=""
    while true; do
        # Prompt the user with a list of known disks
        DIALOG --menu $"Select the disk you want to partition\n(select DONE when finished)" 14 55 7 ${DISCS} 2>${ANSWER} || return 1
        DISC=$(cat ${ANSWER})
        if [[ "${DISC}" == "OTHER" ]]; then
            DIALOG --inputbox $"Enter the full path to the device you wish to partition" 8 65 "/dev/sda" 2>${ANSWER} || DISC=""
            DISC=$(cat ${ANSWER})
        fi
        # Leave our loop if the user is done partitioning
        [[ "${DISC}" == "DONE" ]] && break
        MSDOS_DETECTED=""
        if ! [[ "${DISC}" == "" ]]; then
            if [[ "${GUIDPARAMETER}" == "yes" ]]; then
                CHECK_BIOS_BOOT_GRUB=""
                CHECK_UEFISYS_PART=""
                RUN_CGDISK="1"
                check_gpt
            else
                [[ "$(${_BLKID} -p -i -o value -s PTTYPE ${DISC})" == "dos" ]] && MSDOS_DETECTED="1"
                
                if [[ "${MSDOS_DETECTED}" == "" ]]; then
                    DIALOG --defaultno --yesno $"Setup detected no MS-DOS partition table on ${DISC}.\nDo you want to create a MS-DOS partition table now on ${DISC}?\n\n${DISC} will be COMPLETELY ERASED!  Are you absolutely sure?" 0 0 || return 1
                    # clean partitiontable to avoid issues!
                    dd if=/dev/zero of=${DEVICE} bs=512 count=2048 >/dev/null 2>&1
                    wipefs -a ${DEVICE} /dev/null 2>&1
                    parted -a optimal -s ${DISC} mktable msdos >${LOG}
                fi
                # Partition disc
                DIALOG --msgbox $"Now you'll be put into the parted shell where you can partition your hard drive. You should make a swap partition and as many data partitions as you will need.\n\nShort command list:\n- 'help' to get help text\n- 'print' to show  partition table\n- 'mkpart' for new partition\n- 'rm' for deleting a partition\n- 'quit' to leave parted\n\nNOTE: parted may tell you to reboot after creating partitions.  If you need to reboot, just re-enter this install program, skip this step and go on." 18 70
                clear
                ## Use parted for correct alignment, cfdisk does not align correct!
                parted ${DISC} print
                parted ${DISC}
            fi
        fi
    done
    # update dmraid
    _dmraid_update
    NEXTITEM="3"
    S_PART=1
}

# scan and update btrfs devices
btrfs_scan() {
    btrfs device scan >/dev/null 2>&1
}

# mount btrfs for checks
mount_btrfs() {
    btrfs_scan
    BTRFSMP="$(mktemp -d /tmp/brtfsmp.XXXX)"
    mount ${PART} ${BTRFSMP}
}

# unmount btrfs after checks done
umount_btrfs() {
    umount ${BTRFSMP}
    rm -r ${BTRFSMP}
}

# Set BTRFS_DEVICES on detected btrfs devices
find_btrfs_raid_devices() {
    btrfs_scan
    if [[ "${DETECT_CREATE_FILESYSTEM}" = "no" && "${FSTYPE}" = "btrfs" ]]; then
        for i in $(btrfs filesystem show ${PART} | cut -d " " -f 11); do
            BTRFS_DEVICES="${BTRFS_DEVICES}#${i}"
        done
    fi
}

find_btrfs_raid_bootloader_devices() {
    btrfs_scan
    BTRFS_COUNT=1
    if [[ "$(${_BLKID} -p -i  ${bootdev} -o value -s TYPE)" = "btrfs" ]]; then
        BTRFS_DEVICES=""
        for i in $(btrfs filesystem show ${bootdev} | cut -d " " -f 11); do
            BTRFS_DEVICES="${BTRFS_DEVICES}#${i}"
            BTRFS_COUNT=$((${BTRFS_COUNT}+1))
        done
    fi
}

# find btrfs subvolume
find_btrfs_subvolume() {
    if [[ "${DETECT_CREATE_FILESYSTEM}" = "no" ]]; then
        # existing btrfs subvolumes
        mount_btrfs
        for i in $(btrfs subvolume list ${BTRFSMP} | cut -d " " -f 7); do
            echo ${i}
            [[ "${1}" ]] && echo ${1}
        done
        umount_btrfs
    fi
}

find_btrfs_bootloader_subvolume() {
    BTRFS_SUBVOLUME_COUNT=1
    if [[ "$(${_BLKID} -p -i ${bootdev} -o value -s TYPE)" = "btrfs" ]]; then
        BTRFS_SUBVOLUMES=""
        PART="${bootdev}"
        mount_btrfs
        for i in $(btrfs subvolume list ${BTRFSMP} | cut -d " " -f 7); do
            BTRFS_SUBVOLUMES="${BTRFS_SUBVOLUMES}#${i}"
            BTRFS_SUBVOLUME_COUNT=$((${BTRFS_COUNT}+1))
        done
        umount_btrfs
    fi
}

# subvolumes already in use
subvolumes_in_use() {
    SUBVOLUME_IN_USE=""
    for i in $(grep ${PART}[:#] /tmp/.parts); do
        if [[ "$(echo ${i} | grep ":btrfs:")" ]]; then
            SUBVOLUME_IN_USE="${SUBVOLUME_IN_USE} $(echo ${i} | cut -d: -f 9)"
        fi
    done
}

# ask for btrfs compress option
btrfs_compress() {
    BTRFS_COMPRESS="NONE"
    BTRFS_COMPRESSLEVELS="lzo - zlib -"
    if [[ "${BTRFS_SUBVOLUME}" = "NONE" ]]; then
        DIALOG --defaultno --yesno $"Would you like to compress the data on ${PART}?" 0 0 && BTRFS_COMPRESS="compress"
    else
        DIALOG --defaultno --yesno $"Would you like to compress the data on ${PART} subvolume=${BTRFS_SUBVOLUME}?" 0 0 && BTRFS_COMPRESS="compress"
    fi
    if [[ "${BTRFS_COMPRESS}" = "compress" ]]; then
        DIALOG --menu $"Select the compression method you want to use" 21 50 9 ${BTRFS_COMPRESSLEVELS} 2>${ANSWER} || return 1
        BTRFS_COMPRESS="compress=$(cat ${ANSWER})"
    fi
}

# ask for btrfs ssd option
btrfs_ssd() {
    BTRFS_SSD="NONE"
    if [[ "${BTRFS_SUBVOLUME}" = "NONE" ]]; then
        DIALOG --defaultno --yesno $"Would you like to optimize the data for ssd disk usage on ${PART}?" 0 0 && BTRFS_SSD="ssd"
    else
        DIALOG --defaultno --yesno $"Would you like to optimize the data for ssd disk usage on ${PART} subvolume=${BTRFS_SUBVOLUME}?" 0 0 && BTRFS_SSD="ssd"
    fi
}

# values that are only needed for btrfs creation
clear_btrfs_values() {
    : >/tmp/.btrfs-devices
    LABEL_NAME=""
    FS_OPTIONS=""
    BTRFS_DEVICES=""
    BTRFS_LEVEL=""
}

# do not ask for btrfs filesystem creation, if already prepared for creation!
check_btrfs_filesystem_creation() {
    DETECT_CREATE_FILESYSTEM="no"
    SKIP_FILESYSTEM="no"
    SKIP_ASK_SUBVOLUME="no"
    for i in $(grep ${PART}[:#] /tmp/.parts); do
        if [[ "$(echo ${i} | grep ":btrfs:")" ]]; then
            FSTYPE="btrfs"
            SKIP_FILESYSTEM="yes"
            # check on filesystem creation, skip subvolume asking then!
            [[ "$(echo ${i} | cut -d: -f 4 | grep yes)" ]] && DETECT_CREATE_FILESYSTEM="yes"
            [[ "${DETECT_CREATE_FILESYSTEM}" = "yes" ]] && SKIP_ASK_SUBVOLUME="yes"
        fi
    done
}

# remove devices with no subvolume from list and generate raid device list
btrfs_parts() {
     if [[ -s /tmp/.btrfs-devices ]]; then
         BTRFS_DEVICES=""
         for i in $(cat /tmp/.btrfs-devices); do
             BTRFS_DEVICES="${BTRFS_DEVICES}#${i}"
             # remove device if no subvolume is used!
             [[ "${BTRFS_SUBVOLUME}" = "NONE"  ]] && PARTS="$(echo ${PARTS} | sed -e "s#${i}\ _##g")"
         done
     else
         [[ "${BTRFS_SUBVOLUME}" = "NONE"  ]] && PARTS="$(echo ${PARTS} | sed -e "s#${PART}\ _##g")"
     fi
}

# choose raid level to use on btrfs device
btrfs_raid_level() {
    BTRFS_RAIDLEVELS="NONE - raid0 - raid1 - raid10 - single -"
    BTRFS_RAID_FINISH=""
    BTRFS_LEVEL=""
    BTRFS_DEVICE="${PART}"
    : >/tmp/.btrfs-devices
    DIALOG --msgbox $"BTRFS RAID OPTIONS:\n\nBTRFS has options to control the raid configuration for data and metadata.\nValid choices are raid0, raid1, raid10 and single.\nsingle means that no duplication of metadata is done, which may be desired when using hardware raid. raid10 requires at least 4 devices.\n\nIf you don't need this feature select NONE." 0 0
    while [[ "${BTRFS_RAID_FINISH}" != "DONE" ]]; do
        DIALOG --menu $"Select the raid level you want to use" 21 50 9 ${BTRFS_RAIDLEVELS} 2>${ANSWER} || return 1
        BTRFS_LEVEL=$(cat ${ANSWER})
        if [[ "${BTRFS_LEVEL}" = "NONE" ]]; then
            echo "${BTRFS_DEVICE}" >>/tmp/.btrfs-devices
            break
        else
            # take selected device as 1st device, add additional devices in part below.
            select_btrfs_raid_devices
        fi
    done
}

# select btrfs raid devices
select_btrfs_raid_devices () {
    # show all devices with sizes
    # DIALOG --msgbox "DISKS:\n$(_getavaildisks)\n\nPARTITIONS:\n$(_getavailpartitions)" 0 0
    # select the second device to use, no missing option available!
    : >/tmp/.btrfs-devices
    BTRFS_PART="${BTRFS_DEVICE}"
    BTRFS_PARTS="${PARTS}"
    echo "${BTRFS_PART}" >>/tmp/.btrfs-devices
    BTRFS_PARTS="$(echo ${BTRFS_PARTS} | sed -e "s#${BTRFS_PART}\ _##g")"
    RAIDNUMBER=2
    DIALOG --menu $"Select device ${RAIDNUMBER}" 21 50 13 ${BTRFS_PARTS} 2>${ANSWER} || return 1
    BTRFS_PART=$(cat ${ANSWER})
    echo "${BTRFS_PART}" >>/tmp/.btrfs-devices
    while [[ "${BTRFS_PART}" != "DONE" ]]; do
        BTRFS_DONE=""
        RAIDNUMBER=$((${RAIDNUMBER} + 1))
        # RAID10 need 4 devices!
        [[ "${RAIDNUMBER}" -ge 3 && ! "${BTRFS_LEVEL}" = "raid10" ]] && BTRFS_DONE="DONE _"
        [[ "${RAIDNUMBER}" -ge 5 && "${BTRFS_LEVEL}" = "raid10" ]] && BTRFS_DONE="DONE _"
        # clean loop from used partition and options
        BTRFS_PARTS="$(echo ${BTRFS_PARTS} | sed -e "s#${BTRFS_PART}\ _##g")"
        # add more devices
        DIALOG --menu $"Select device ${RAIDNUMBER}" 21 50 13 ${BTRFS_PARTS} ${BTRFS_DONE} 2>${ANSWER} || return 1
        BTRFS_PART=$(cat ${ANSWER})
        [[ "${BTRFS_PART}" = "DONE" ]] && break
        echo "${BTRFS_PART}" >>/tmp/.btrfs-devices
     done
     # final step ask if everything is ok?
     DIALOG --yesno $"Would you like to create btrfs raid like this?\n\nLEVEL:\n${BTRFS_LEVEL}\n\nDEVICES:\n$(for i in $(cat /tmp/.btrfs-devices); do echo "${i}\n"; done)" 0 0 && BTRFS_RAID_FINISH="DONE"
}

# prepare new btrfs device
prepare_btrfs() {
    btrfs_raid_level || return 1
    prepare_btrfs_subvolume || return 1
}

# prepare btrfs subvolume
prepare_btrfs_subvolume() {
    DOSUBVOLUME="no"
    BTRFS_SUBVOLUME="NONE"
    if [[ "${SKIP_ASK_SUBVOLUME}" = "no" ]]; then
        DIALOG --defaultno --yesno $"Would you like to create a new subvolume on ${PART}?" 0 0 && DOSUBVOLUME="yes"
    else
        DOSUBVOLUME="yes"
    fi
    if [[ "${DOSUBVOLUME}" = "yes" ]]; then
        BTRFS_SUBVOLUME="NONE"
        while [[ "${BTRFS_SUBVOLUME}" = "NONE" ]]; do
            DIALOG --inputbox $"Enter the SUBVOLUME name for the device, keep it short\nand use no spaces or special\ncharacters." 10 65 2>${ANSWER} || return 1
            BTRFS_SUBVOLUME=$(cat ${ANSWER})
            check_btrfs_subvolume
        done
    else
        BTRFS_SUBVOLUME="NONE"
    fi
}

# check btrfs subvolume
check_btrfs_subvolume(){
    [[ "${DOMKFS}" = "yes" && "${FSTYPE}" = "btrfs" ]] && DETECT_CREATE_FILESYSTEM="yes"
    if [[ "${DETECT_CREATE_FILESYSTEM}" = "no" ]]; then
        mount_btrfs
        for i in $(btrfs subvolume list ${BTRFSMP} | cut -d " " -f 7); do
            if [[ "$(echo ${i} | grep "${BTRFS_SUBVOLUME}"$)" ]]; then
                DIALOG --msgbox $"ERROR: You have defined 2 identical SUBVOLUME names or an empty name! Please enter another name." 8 65
                BTRFS_SUBVOLUME="NONE"
            fi
        done
        umount_btrfs
    else
        subvolumes_in_use
        if [[ "$(echo ${SUBVOLUME_IN_USE} | egrep "${BTRFS_SUBVOLUME}")" ]]; then
            DIALOG --msgbox $"ERROR: You have defined 2 identical SUBVOLUME names or an empty name! Please enter another name." 8 65
            BTRFS_SUBVOLUME="NONE"
        fi
    fi
}

# create btrfs subvolume
create_btrfs_subvolume() {
    mount_btrfs
    btrfs subvolume create ${BTRFSMP}/${_btrfssubvolume} >${LOG}
    # change permission from 700 to 755 
    # to avoid warnings during package installation
    chmod 755 ${BTRFSMP}/${_btrfssubvolume}
    umount_btrfs
}

# choose btrfs subvolume from list
choose_btrfs_subvolume () {
    BTRFS_SUBVOLUME="NONE"
    SUBVOLUMES_DETECTED="no"
    SUBVOLUMES=$(find_btrfs_subvolume _)
    # check if subvolumes are present
    [[ -n "${SUBVOLUMES}" ]] && SUBVOLUMES_DETECTED="yes"
    subvolumes_in_use
    for i in ${SUBVOLUME_IN_USE}; do
        SUBVOLUMES=$(echo ${SUBVOLUMES} | sed -e "s#${i}\ _##g")
    done
    if [[ -n "${SUBVOLUMES}" ]]; then
        DIALOG --menu $"Select the subvolume to mount" 21 50 13 ${SUBVOLUMES} 2>${ANSWER} || return 1
        BTRFS_SUBVOLUME=$(cat ${ANSWER})
    else
        if [[ "${SUBVOLUMES_DETECTED}" = "yes" ]]; then
            DIALOG --msgbox $"ERROR: All subvolumes of the device are already in use. Switching to create a new one now." 8 65
            SKIP_ASK_SUBVOLUME=yes
            prepare_btrfs_subvolume || return 1
        fi
    fi
}

# boot on btrfs subvolume is not supported
check_btrfs_boot_subvolume() {
    if [[ "${MP}" = "/boot" && "${FSTYPE}" = "btrfs" && ! "${BTRFS_SUBVOLUME}" = "NONE" ]]; then
        DIALOG --msgbox $"ERROR: \n/boot on a btrfs subvolume is not supported by any bootloader yet!" 8 65
        FILESYSTEM_FINISH="no"
    fi
}

# btrfs subvolume menu
btrfs_subvolume() {
    FILESYSTEM_FINISH=""
    if [[ "${FSTYPE}" = "btrfs" && "${DOMKFS}" = "no" ]]; then
        if [[ "${ASK_MOUNTPOINTS}" = "1" ]]; then
            # create subvolume if requested
            # choose btrfs subvolume if present
            prepare_btrfs_subvolume || return 1
            if [[ "${BTRFS_SUBVOLUME}" = "NONE" ]]; then
                choose_btrfs_subvolume || return 1
            fi
        else
            # use device if no subvolume is present
            choose_btrfs_subvolume || return 1
        fi
        btrfs_compress
        btrfs_ssd
    fi
    FILESYSTEM_FINISH="yes"
}

select_filesystem() {
    FILESYSTEM_FINISH=""
    # don't allow vfat as / filesystem, it will not work!
    # don't allow ntfs as / filesystem, this is stupid!
    FSOPTS=""
    [[ "$(which mkfs.ext2 2>/dev/null)" ]] && FSOPTS="${FSOPTS} ext2 Ext2"
    [[ "$(which mkfs.ext3 2>/dev/null)" ]] && FSOPTS="${FSOPTS} ext3 Ext3"
    [[ "$(which mkfs.ext4 2>/dev/null)" ]] && FSOPTS="${FSOPTS} ext4 Ext4"
    [[ "$(which mkfs.btrfs 2>/dev/null)" ]] && FSOPTS="${FSOPTS} btrfs Btrfs-(Experimental)"
    [[ "$(which mkfs.nilfs2 2>/dev/null)" ]] && FSOPTS="${FSOPTS} nilfs2 Nilfs2-(Experimental)"
    [[ "$(which mkreiserfs 2>/dev/null)" ]] && FSOPTS="${FSOPTS} reiserfs Reiser3"
    [[ "$(which mkfs.xfs 2>/dev/null)" ]] && FSOPTS="${FSOPTS} xfs XFS"
    [[ "$(which mkfs.jfs 2>/dev/null)" ]] && FSOPTS="${FSOPTS} jfs JFS"
    [[ "$(which mkfs.ntfs 2>/dev/null)" && "${DO_ROOT}" = "DONE" ]] && FSOPTS="${FSOPTS} ntfs-3g NTFS"
    [[ "$(which mkfs.vfat 2>/dev/null)" && "${DO_ROOT}" = "DONE" ]] && FSOPTS="${FSOPTS} vfat VFAT"
    DIALOG --menu $"Select a filesystem for ${PART}" 21 50 13 ${FSOPTS} 2>${ANSWER} || return 1
    FSTYPE=$(cat ${ANSWER})
}

enter_mountpoint() {
    FILESYSTEM_FINISH=""
    MP=""
    while [[ "${MP}" = "" ]]; do
        DIALOG --inputbox $"Enter the mountpoint for ${PART}" 8 65 "/boot" 2>${ANSWER} || return 1
        MP=$(cat ${ANSWER})
        if grep ":${MP}:" /tmp/.parts; then
            DIALOG --msgbox $"ERROR: You have defined 2 identical mountpoints! Please select another mountpoint." 8 65
            MP=""
        fi
    done
}

# set sane values for paramaters, if not already set
check_mkfs_values() {
    # Set values, to not confuse mkfs call!
    [[ "${FS_OPTIONS}" = "" ]] && FS_OPTIONS="NONE"
    [[ "${BTRFS_DEVICES}" = "" ]] && BTRFS_DEVICES="NONE"
    [[ "${BTRFS_LEVEL}" = "" ]] && BTRFS_LEVEL="NONE"
    [[ "${BTRFS_SUBVOLUME}" = "" ]] && BTRFS_SUBVOLUME="NONE"
    [[ "${DOSUBVOLUME}" = "" ]] && DOSUBVOLUME="no"
    [[ "${LABEL_NAME}" = "" && -n "$(${_BLKID} -p -i -o value -s LABEL ${PART})" ]] && LABEL_NAME="$(${_BLKID} -p -i -o value -s LABEL ${PART})"
    [[ "${LABEL_NAME}" = "" ]] && LABEL_NAME="NONE"
}

create_filesystem() {
    FILESYSTEM_FINISH=""
    LABEL_NAME=""
    FS_OPTIONS=""
    BTRFS_DEVICES=""
    BTRFS_LEVEL=""
    DIALOG --yesno $"Would you like to create a filesystem on ${PART}?\n\n(This will overwrite existing data!)" 0 0 && DOMKFS="yes"
    if [[ "${DOMKFS}" = "yes" ]]; then
        while [[ "${LABEL_NAME}" = "" ]]; do
            DIALOG --inputbox $"Enter the LABEL name for the device, keep it short\n(not more than 12 characters) and use no spaces or special\ncharacters." 10 65 \
            "$(${_BLKID} -p -i -o value -s LABEL ${PART})" 2>${ANSWER} || return 1
            LABEL_NAME=$(cat ${ANSWER})
            if grep ":${LABEL_NAME}$" /tmp/.parts; then
                DIALOG --msgbox $"ERROR: You have defined 2 identical LABEL names! Please enter another name." 8 65
                LABEL_NAME=""
            fi
        done
        if [[ "${FSTYPE}" = "btrfs" ]]; then
            prepare_btrfs || return 1
            btrfs_compress
            btrfs_ssd
        fi
        DIALOG --inputbox $"Enter additional options to the filesystem creation utility.\nUse this field only, if the defaults are not matching your needs,\nelse just leave it empty." 10 70  2>${ANSWER} || return 1
        FS_OPTIONS=$(cat ${ANSWER})
    fi
    FILESYSTEM_FINISH="yes"
}

mountpoints() {
    NAME_SCHEME_PARAMETER_RUN=""
    while [[ "${PARTFINISH}" != "DONE" ]]; do
        activate_special_devices
        : >/tmp/.device-names
        : >/tmp/.fstab
        : >/tmp/.parts
        #
        # Select mountpoints
        #
        DIALOG --msgbox $"Available partitions:\n\n$(_getavailpartitions)\n" 0 0
        PARTS=$(findpartitions _)
        DO_SWAP=""
        while [[ "${DO_SWAP}" != "DONE" ]]; do
            FSTYPE="swap"
            DIALOG --menu $"Select the partition to use as swap" 21 50 13 NONE - ${PARTS} 2>${ANSWER} || return 1
            PART=$(cat ${ANSWER})
            if [[ "${PART}" != "NONE" ]]; then
                DOMKFS="no"
                if [[ "${ASK_MOUNTPOINTS}" = "1" ]]; then
                    create_filesystem
                else
                    FILESYSTEM_FINISH="yes"
                fi
            else
                FILESYSTEM_FINISH="yes"
            fi
            [[ "${FILESYSTEM_FINISH}" = "yes" ]] && DO_SWAP=DONE
        done
        check_mkfs_values
        if [[ "${PART}" != "NONE" ]]; then
            PARTS="$(echo ${PARTS} | sed -e "s#${PART}\ _##g")"
            echo "${PART}:swap:swap:${DOMKFS}:${LABEL_NAME}:${FS_OPTIONS}:${BTRFS_DEVICES}:${BTRFS_LEVEL}:${BTRFS_SUBVOLUME}:${DOSUBVOLUME}:${BTRFS_COMPRESS}:${BTRFS_SSD}" >>/tmp/.parts
        fi
        DO_ROOT=""
        while [[ "${DO_ROOT}" != "DONE" ]]; do
            DIALOG --menu $"Select the partition to mount as /" 21 50 13 ${PARTS} 2>${ANSWER} || return 1
            PART=$(cat ${ANSWER})
            PART_ROOT=${PART}
            # Select root filesystem type
            FSTYPE="$(${_BLKID} -p -i -o value -s TYPE ${PART})"
            DOMKFS="no"
            # clear values first!
            clear_btrfs_values
            check_btrfs_filesystem_creation
            if [[ "${ASK_MOUNTPOINTS}" = "1" && "${SKIP_FILESYSTEM}" = "no" ]]; then
                select_filesystem && create_filesystem && btrfs_subvolume
            else                   
                btrfs_subvolume
            fi
            [[ "${FILESYSTEM_FINISH}" = "yes" ]] && DO_ROOT=DONE
        done
        find_btrfs_raid_devices
        btrfs_parts
        check_mkfs_values
        echo "${PART}:${FSTYPE}:/:${DOMKFS}:${LABEL_NAME}:${FS_OPTIONS}:${BTRFS_DEVICES}:${BTRFS_LEVEL}:${BTRFS_SUBVOLUME}:${DOSUBVOLUME}:${BTRFS_COMPRESS}:${BTRFS_SSD}" >>/tmp/.parts
        ! [[ "${FSTYPE}" = "btrfs" ]] && PARTS="$(echo ${PARTS} | sed -e "s#${PART}\ _##g")"
        #
        # Additional partitions
        #
        while [[ "${PART}" != "DONE" ]]; do
            DO_ADDITIONAL=""
            while [[ "${DO_ADDITIONAL}" != "DONE" ]]; do
                DIALOG --menu $"Select any additional partitions to mount under your new root (select DONE when finished)" 21 52 13 ${PARTS} DONE _ 2>${ANSWER} || return 1
                PART=$(cat ${ANSWER})
                if [[ "${PART}" != "DONE" ]]; then
                    FSTYPE="$(${_BLKID} -p -i  -o value -s TYPE ${PART})"
                    DOMKFS="no"
                    # clear values first!
                    clear_btrfs_values
                    check_btrfs_filesystem_creation
                    # Select a filesystem type
                    if [[ "${ASK_MOUNTPOINTS}" = "1" && "${SKIP_FILESYSTEM}" = "no" ]]; then
                        enter_mountpoint && select_filesystem && create_filesystem && btrfs_subvolume
                    else
                        enter_mountpoint
                        btrfs_subvolume
                    fi
                    check_btrfs_boot_subvolume
                else
                    FILESYSTEM_FINISH="yes"
                fi
                [[ "${FILESYSTEM_FINISH}" = "yes" ]] && DO_ADDITIONAL="DONE"
            done
            if [[ "${PART}" != "DONE" ]]; then
                find_btrfs_raid_devices
                btrfs_parts
                check_mkfs_values
                echo "${PART}:${FSTYPE}:${MP}:${DOMKFS}:${LABEL_NAME}:${FS_OPTIONS}:${BTRFS_DEVICES}:${BTRFS_LEVEL}:${BTRFS_SUBVOLUME}:${DOSUBVOLUME}:${BTRFS_COMPRESS}:${BTRFS_SSD}" >>/tmp/.parts
                ! [[ "${FSTYPE}" = "btrfs" ]] && PARTS="$(echo ${PARTS} | sed -e "s#${PART}\ _##g")"
            fi
        done
        DIALOG --yesno $"Would you like to create and mount the filesytems like this?\n\nSyntax\n------\nDEVICE:TYPE:MOUNTPOINT:FORMAT:LABEL:FSOPTIONS:BTRFS_DETAILS\n\n$(for i in $(cat /tmp/.parts | sed -e 's, ,#,g'); do echo "${i}\n";done)" 0 0 && PARTFINISH="DONE"
    done
    # disable swap and all mounted partitions
    _umountall
    if [[ "${NAME_SCHEME_PARAMETER_RUN}" = "" ]]; then
        set_device_name_scheme || return 1
    fi
    for line in $(cat /tmp/.parts); do
        PART=$(echo ${line} | cut -d: -f 1)
        FSTYPE=$(echo ${line} | cut -d: -f 2)
        MP=$(echo ${line} | cut -d: -f 3)
        DOMKFS=$(echo ${line} | cut -d: -f 4)
        LABEL_NAME=$(echo ${line} | cut -d: -f 5)
        FS_OPTIONS=$(echo ${line} | cut -d: -f 6)
        BTRFS_DEVICES=$(echo ${line} | cut -d: -f 7)
        BTRFS_LEVEL=$(echo ${line} | cut -d: -f 8)
        BTRFS_SUBVOLUME=$(echo ${line} | cut -d: -f 9)
        DOSUBVOLUME=$(echo ${line} | cut -d: -f 10)
        BTRFS_COMPRESS=$(echo ${line} | cut -d: -f 11)
        BTRFS_SSD=$(echo ${line} | cut -d: -f 12)
        if [[ "${DOMKFS}" = "yes" ]]; then
            if [[ "${FSTYPE}" = "swap" ]]; then
                DIALOG --infobox $"Creating and activating swapspace on ${PART}" 0 0
            else
                DIALOG --infobox $"Creating ${FSTYPE} on ${PART},\nmounting to ${DESTDIR}${MP}" 0 0
            fi
            _mkfs yes ${PART} ${FSTYPE} ${DESTDIR} ${MP} ${LABEL_NAME} ${FS_OPTIONS} ${BTRFS_DEVICES} ${BTRFS_LEVEL} ${BTRFS_SUBVOLUME} ${DOSUBVOLUME} ${BTRFS_COMPRESS} ${BTRFS_SSD} || return 1
        else
            if [[ "${FSTYPE}" = "swap" ]]; then
                DIALOG --infobox $"Activating swapspace on ${PART}" 0 0
            else
                DIALOG --infobox $"Mounting ${FSTYPE} on ${PART} to ${DESTDIR}${MP}" 0 0
            fi
            _mkfs no ${PART} ${FSTYPE} ${DESTDIR} ${MP} ${LABEL_NAME} ${FS_OPTIONS} ${BTRFS_DEVICES} ${BTRFS_LEVEL} ${BTRFS_SUBVOLUME} ${DOSUBVOLUME} ${BTRFS_COMPRESS} ${BTRFS_SSD} || return 1
        fi
        sleep 1
    done

    DIALOG --msgbox $"Partitions were successfully mounted." 0 0
    NEXTITEM="5"
    S_MKFS=1
}

# _mkfs()
# Create and mount filesystems in our destination system directory.
#
# args:
#  domk: Whether to make the filesystem or use what is already there
#  device: Device filesystem is on
#  fstype: type of filesystem located at the device (or what to create)
#  dest: Mounting location for the destination system
#  mountpoint: Mount point inside the destination system, e.g. '/boot'

# returns: 1 on failure
_mkfs() {
    local _domk=${1}
    local _device=${2}
    local _fstype=${3}
    local _dest=${4}
    local _mountpoint=${5}
    local _labelname=${6}
    local _fsoptions=${7}
    local _btrfsdevices="$(echo ${8} | sed -e 's|#| |g')"
    local _btrfslevel=${9}
    local _btrfssubvolume=${10}
    local _dosubvolume=${11}
    local _btrfscompress=${12}
    local _btrfsssd=${13}
    # correct empty entries
    [[ "${_fsoptions}" = "NONE" ]] && _fsoptions=""
    [[ "${_btrfsssd}" = "NONE" ]] && _btrfsssd=""
    [[ "${_btrfscompress}" = "NONE" ]] && _btrfscompress=""
    [[ "${_btrfssubvolume}" = "NONE" ]] && _btrfssubvolume=""
    # add btrfs raid level, if needed
    [[ ! "${_btrfslevel}" = "NONE" && "${_fstype}" = "btrfs" ]] && _fsoptions="${_fsoptions} -d ${_btrfslevel}"
    # we have two main cases: "swap" and everything else.
    if [[ "${_fstype}" = "swap" ]]; then
        swapoff ${_device} >/dev/null 2>&1
        if [[ "${_domk}" = "yes" ]]; then
            mkswap -L ${_labelname} ${_device} >${LOG} 2>&1
            if [[ $? != 0 ]]; then
                DIALOG --msgbox $"Error creating swap: mkswap ${_device}" 0 0
                return 1
            fi
        fi
        swapon ${_device} >${LOG} 2>&1
        if [[ $? != 0 ]]; then
            DIALOG --msgbox $"Error activating swap: swapon ${_device}" 0 0
            return 1
        fi
    else
        # make sure the fstype is one we can handle
        local knownfs=0
        for fs in xfs jfs reiserfs ext2 ext3 ext4 btrfs nilfs2 ntfs-3g vfat; do
            [[ "${_fstype}" = "${fs}" ]] && knownfs=1 && break
        done
        if [[ ${knownfs} -eq 0 ]]; then
            DIALOG --msgbox $"unknown fstype ${_fstype} for ${_device}" 0 0
            return 1
        fi
        # if we were tasked to create the filesystem, do so
        if [[ "${_domk}" = "yes" ]]; then
            local ret
            case ${_fstype} in
                xfs)      mkfs.xfs ${_fsoptions} -L ${_labelname} -f ${_device} >${LOG} 2>&1; ret=$? ;;
                jfs)      yes | mkfs.jfs ${_fsoptions} -L ${_labelname} ${_device} >${LOG} 2>&1; ret=$? ;;
                reiserfs) yes | mkreiserfs ${_fsoptions} -l ${_labelname} ${_device} >${LOG} 2>&1; ret=$? ;;
                ext2)     mkfs.ext2 -L ${_fsoptions} ${_labelname} ${_device} >${LOG} 2>&1; ret=$? ;;
                ext3)     mke2fs ${_fsoptions} -L ${_labelname} -t ext3 ${_device} >${LOG} 2>&1; ret=$? ;;
                ext4)     mke2fs ${_fsoptions} -L ${_labelname} -t ext4 ${_device} >${LOG} 2>&1; ret=$? ;;
                btrfs)    mkfs.btrfs ${_fsoptions} -L ${_labelname} ${_btrfsdevices} >${LOG} 2>&1; ret=$? ;;
                nilfs2)   mkfs.nilfs2 ${_fsoptions} -L ${_labelname} ${_device} >${LOG} 2>&1; ret=$? ;;
                ntfs-3g)  mkfs.ntfs ${_fsoptions} -L ${_labelname} ${_device} >${LOG} 2>&1; ret=$? ;;
                vfat)     mkfs.vfat ${_fsoptions} -n ${_labelname} ${_device} >${LOG} 2>&1; ret=$? ;;
                # don't handle anything else here, we will error later
            esac
            if [[ ${ret} != 0 ]]; then
                DIALOG --msgbox $"Error creating filesystem ${_fstype} on ${_device}" 0 0
                return 1
            fi
            sleep 2
        fi
        if [[ "${_fstype}" = "btrfs" && -n "${_btrfssubvolume}" && "${_dosubvolume}" = "yes" ]]; then
            create_btrfs_subvolume
        fi
        btrfs_scan
        sleep 2
        # create our mount directory
        mkdir -p ${_dest}${_mountpoint}
        # prepare btrfs mount options
        _btrfsmountoptions=""
        [[ -n "${_btrfssubvolume}" ]] && _btrfsmountoptions="subvol=${_btrfssubvolume}"
        [[ -n "${_btrfscompress}" ]] && _btrfsmountoptions="${_btrfsmountoptions} ${_btrfscompress}"
        [[ -n "${_btrfsssd}" ]] && _btrfsmountoptions="${_btrfsmountoptions} ${_btrfsssd}"
        _btrfsmountoptions="$(echo ${_btrfsmountoptions} | sed -e 's#^ ##g' | sed -e 's# #,#g')"
        # mount the bad boy
        if [[ "${_fstype}" = "btrfs" && -n "${_btrfsmountoptions}" ]]; then
            mount -t ${_fstype} -o ${_btrfsmountoptions} ${_device} ${_dest}${_mountpoint} >${LOG} 2>&1
        else
            mount -t ${_fstype} ${_device} ${_dest}${_mountpoint} >${LOG} 2>&1
        fi
        if [[ $? != 0 ]]; then
            DIALOG --msgbox $"Error mounting ${_dest}${_mountpoint}" 0 0
            return 1
        fi
        # change permission of base directories to correct permission
        # to avoid btrfs issues
        if [[ "${_mountpoint}" = "/tmp" ]]; then
            chmod 1777 ${_dest}${_mountpoint}
        elif [[ "${_mountpoint}" = "/root" ]]; then
            chmod 750 ${_dest}${_mountpoint}
        else
            chmod 755 ${_dest}${_mountpoint}
        fi
    fi
    # add to .device-names for config files
    local _fsuuid="$(getfsuuid ${_device})"
    local _fslabel="$(getfslabel ${_device})"
    
    if [[ "${GUID_DETECTED}" == "1" ]]; then
        local _partuuid="$(getpartuuid ${_device})"
        local _partlabel="$(getpartlabel ${_device})"
        
        echo "# DEVICE DETAILS: ${_device} PARTUUID=${_partuuid} PARTLABEL=${_partlabel} UUID=${_fsuuid} LABEL=${_fslabel}" >> /tmp/.device-names
    else
        echo "# DEVICE DETAILS: ${_device} UUID=${_fsuuid} LABEL=${_fslabel}" >> /tmp/.device-names
    fi

    # add to temp fstab
    if [[ "${NAME_SCHEME_PARAMETER}" == "FSUUID" ]]; then
        if [[ -n "${_fsuuid}" ]]; then
            _device="UUID=${_fsuuid}"
        fi
    elif [[ "${NAME_SCHEME_PARAMETER}" == "FSLABEL" ]]; then
        if [[ -n "${_fslabel}" ]]; then
            _device="LABEL=${_fslabel}"
        fi
    else
        if [[ "${GUID_DETECTED}" == "1" ]]; then
           if [[ "${NAME_SCHEME_PARAMETER}" == "PARTUUID" ]]; then
               if [[ -n "${_partuuid}" ]]; then
                   _device="PARTUUID=${_partuuid}"
               fi
           elif [[ "${NAME_SCHEME_PARAMETER}" == "PARTLABEL" ]]; then
               if [[ -n "${_partlabel}" ]]; then
                   _device="PARTLABEL=${_partlabel}"
               fi
           fi 
        fi
    fi
    if [[ "${_fstype}" = "btrfs" && -n "${_btrfsmountoptions}" ]]; then
        echo -n "${_device} ${_mountpoint} ${_fstype} defaults,${_btrfsmountoptions} 0 " >>/tmp/.fstab
    else
        echo -n "${_device} ${_mountpoint} ${_fstype} defaults 0 " >>/tmp/.fstab
    fi
    if [[ "${_fstype}" = "swap" ]]; then
        echo "0" >>/tmp/.fstab
    else
        echo "1" >>/tmp/.fstab
    fi
}


# pacman_conf()
# creates temporary pacman.conf file
pacman_conf() {

        if [[ $(uname -m) = 'i686' ]];then
    cat << EOF > /tmp/pacman.conf
[options]
Architecture = auto
SigLevel = PackageOptional
CacheDir = ${DESTDIR}/var/cache/pacman/pkg
CacheDir = /packages/core-$(uname -m)/pkg
CacheDir = /packages/core-any/pkg

###### Repos from www.cinnarch.com ######
[cinnarch-core]
SigLevel = PackageRequired
Include = /etc/pacman.d/cinnarch-mirrorlist

[cinnarch-repo]
SigLevel = PackageRequired
Include = /etc/pacman.d/cinnarch-mirrorlist
###### Repos from www.cinnarch.com ######

[core]
SigLevel = PackageRequired
Include = /etc/pacman.d/mirrorlist

[extra]
SigLevel = PackageRequired
Include = /etc/pacman.d/mirrorlist

[community]
SigLevel = PackageRequired
Include = /etc/pacman.d/mirrorlist

EOF

        else
            cat << EOF > /tmp/pacman.conf
[options]
Architecture = auto
SigLevel = PackageOptional
CacheDir = ${DESTDIR}/var/cache/pacman/pkg
CacheDir = /packages/core-$(uname -m)/pkg
CacheDir = /packages/core-any/pkg

###### Repos from www.cinnarch.com ######
[cinnarch-core]
SigLevel = PackageRequired
Include = /etc/pacman.d/cinnarch-mirrorlist

[cinnarch-repo]
SigLevel = PackageRequired
Include = /etc/pacman.d/cinnarch-mirrorlist
###### Repos from www.cinnarch.com ######

[core]
SigLevel = PackageRequired
Include = /etc/pacman.d/mirrorlist

[extra]
SigLevel = PackageRequired
Include = /etc/pacman.d/mirrorlist

[community]
SigLevel = PackageRequired
Include = /etc/pacman.d/mirrorlist

[multilib]
SigLevel = PackageRequired
Include = /etc/pacman.d/mirrorlist

EOF

        fi

}

pacman_secinstall_conf() {


        if [[ $(uname -m) = 'i686' ]];then
    cat << EOF > /tmp/pacman.conf
[options]
Architecture = auto
SigLevel = PackageOptional
CacheDir = ${DESTDIR}/var/cache/pacman/pkg
CacheDir = /packages/core-$(uname -m)/pkg
CacheDir = /packages/core-any/pkg

###### Repos from www.cinnarch.com ######
[cinnarch-secinstall]
Include = /etc/pacman.d/cinnarch-mirrorlist
###### Repos from www.cinnarch.com ######

[core]
SigLevel = PackageRequired
Include = /etc/pacman.d/mirrorlist

[extra]
SigLevel = PackageRequired
Include = /etc/pacman.d/mirrorlist

[community]
SigLevel = PackageRequired
Include = /etc/pacman.d/mirrorlist

EOF

        else
            cat << EOF > /tmp/pacman.conf
[options]
Architecture = auto
SigLevel = PackageOptional
CacheDir = ${DESTDIR}/var/cache/pacman/pkg
CacheDir = /packages/core-$(uname -m)/pkg
CacheDir = /packages/core-any/pkg

###### Repos from www.cinnarch.com ######
[cinnarch-secinstall]
Include = /etc/pacman.d/cinnarch-mirrorlist
###### Repos from www.cinnarch.com ######

[core]
SigLevel = PackageRequired
Include = /etc/pacman.d/mirrorlist

[extra]
SigLevel = PackageRequired
Include = /etc/pacman.d/mirrorlist

[community]
SigLevel = PackageRequired
Include = /etc/pacman.d/mirrorlist

[multilib]
SigLevel = PackageRequired
Include = /etc/pacman.d/mirrorlist

EOF

        fi

}

# pacman needs a masterkey before checking signed packages
prepare_pacman_keychain() {
    # Generate initial keychain, use haveged then no user interaction is required
    if  [[ -f /var/run/haveged.pid ]]; then
        kill $(cat /var/run/haveged.pid)
    fi
    haveged
    pacman-key --init >/dev/null 2>&1
    ### HACK: fix accept of master keys!
    sed -i -e 's#"${GPG_PACMAN\[\@\]}" --quiet --lsign-key "${key_id}"#"${GPG_PACMAN\[\@\]}" --batch --yes --quiet --lsign-key "${key_id}"#g' \
    /usr/bin/pacman-key
    pacman-key --populate archlinux cinnarch >/dev/null 2>&1
    sed -i -e 's#"${GPG_PACMAN\[\@\]}" --batch --yes --quiet --lsign-key "${key_id}"#"${GPG_PACMAN\[\@\]}" --quiet --lsign-key "${key_id}"#g' \
    /usr/bin/pacman-key
    kill $(cat /var/run/haveged.pid)
}

# configures pacman and syncs db on destination system
# params: none
# returns: 1 on error
prepare_pacman() {
    local _state_sync=''
    local _arch=`uname -m`
    local PACMAN_SYNC_LOG='/tmp/pacman-sync.log'

    # Set up the necessary directories for pacman use
    [[ ! -d "${DESTDIR}/var/cache/pacman/pkg" ]] && mkdir -m 755 -p "${DESTDIR}/var/cache/pacman/pkg"
    [[ ! -d "${DESTDIR}/var/lib/pacman" ]] && mkdir -m 755 -p "${DESTDIR}/var/lib/pacman"
    prepare_pacman_keychain

    while [[ "${_state_sync}" != 'complete' ]];do
        DIALOG --infobox $"Refreshing package database..." 6 45
        ${PACMAN} -Sy >${LOG} 2>${PACMAN_SYNC_LOG} || return 1
        if [[ $? -ne 0 ]]; then
            DIALOG --msgbox $"Pacman preparation failed! Check ${LOG} for errors." 6 60
            return 1
        fi
        if [[ `grep error ${PACMAN_SYNC_LOG}` ]];then
            _state_sync='missing'
        else
            _state_sync='complete'
        fi
    done
    return 0
}

# Set PACKAGES parameter before running to install wanted packages
run_pacman(){
    local _result=''
    local _check=''
    # create chroot environment on target system
    # code straight from mkarchroot
    chroot_mount

    # execute pacman in a subshell so we can follow its progress
    # pacman output goes /tmp/pacman.log
    # /tmp/setup-pacman-running acts as a lockfile

    while [[ "${_result}" != 'Installation Complete' ]];do
        ( \
            echo "Installing Packages..." >/tmp/pacman.log ; \
            echo >>/tmp/pacman.log ; \
            touch /tmp/setup-pacman-running ; \
            ${PACMAN} -S ${PACKAGES} >>/tmp/pacman.log 2>&1 >> /tmp/pacman.log ; \
            echo $? > /tmp/.pacman-retcode ; \
            if [[ $(cat /tmp/.pacman-retcode) -ne 0 ]]; then
                echo -e "\nPackage Installation FAILED." >>/tmp/pacman.log
            else
                echo -e "\nPackage Installation Complete." >>/tmp/pacman.log
            fi
            rm /tmp/setup-pacman-running
        ) &

        # display pacman output while it's running
        sleep 2
        dialog --backtitle "${TITLE}" --title $" Installing... Please Wait " \
            --no-kill --tailboxbg "/tmp/pacman.log" 18 70 2>${ANSWER}
        while [[ -f /tmp/setup-pacman-running ]]; do
            /bin/true
        done
        kill $(cat ${ANSWER})

        # pacman finished, display scrollable output
        local _result=''
        local _check=''
        if [[ $(cat /tmp/.pacman-retcode) -ne 0 ]]; then
            _result=$"Regular installation Failed. \n\nPress Continue to launch a secure installation.\n\nThis will install your system from a controlled repository in case that your problem comes with a breakage in archlinux repositories"
        else
            _result=$"Installation Complete"
            _check='installed'
        fi
        rm /tmp/.pacman-retcode

        if [[ "${_check}" = 'installed' ]];then
            DIALOG --msgbox "${_result}" 8 50 || return 1
        else
            DIALOG --msgbox "${_result}" 15 60 || return 1
            pacman_secinstall_conf
            prepare_pacman

        fi
    done
    # ensure the disk is synced
    sync
    chroot_umount
}

# select_packages()
# prompts the user to select packages to install
#
# params: none
# returns: 1 on error
select_packages() {
    pacman_conf
    prepare_pacman
    
        # if selection has been done before, warn about loss of input
        # and let the user exit gracefully
        if [[ ${S_SELECT} -ne 0 ]]; then
            DIALOG --yesno $"WARNING: Running this stage again will result in the loss of previous package selections.\n\nDo you wish to continue?" 10 50 || return 1
        fi

        local _pkglist=()
        : >/tmp/package-process.log
        # display pkglist output while it's running
    


  
    # Add packages which are not in core repository
    if [[ "$(grep -w uvesafb /proc/cmdline)" ]]; then
        ! [[ "$(echo ${PACKAGES} | grep -w v86d)" ]] && PACKAGES="${PACKAGES} v86d"
    fi

    #PACKAGES="${PACKAGES} $(cat /run/archiso/bootmnt/arch/pkglist.x86_64.txt)"

    PACKAGES="${PACKAGES} base base-devel cinnarch-meta libgnomeui"

    if [[ -f /tmp/use_ntp ]];then
        PACKAGES="${PACKAGES} ntp"
    fi

    GRAPHIC_CARD=`hwinfo --gfxcard|grep 'Model:[[:space:]]'`
    WLAN_CARD=`hwinfo --wlan --short`

    if [[ `echo ${GRAPHIC_CARD}|grep -i 'ati[[:space:]]'` != "" ]];then
        PACKAGES="${PACKAGES} xf86-video-ati ati-dri"
        touch /tmp/card_ati
    fi

    if [[ `echo ${GRAPHIC_CARD}|grep -i 'nvidia[[:space:]]'` != "" ]];then
        PACKAGES="${PACKAGES} xf86-video-nouveau nouveau-dri"
        touch /tmp/card_nvidia
    fi

    if [[ `echo ${GRAPHIC_CARD}|grep -i 'intel[[:space:]]'` != "" ]];then
        PACKAGES="${PACKAGES} xf86-video-intel intel-dri"
        touch /tmp/card_intel
    fi

    if [[ `echo ${GRAPHIC_CARD}|grep -i 'lenovo[[:space:]]'` != "" ]];then
        PACKAGES="${PACKAGES} xf86-video-intel intel-dri"
        touch /tmp/card_intel
    fi

    if [[ `echo ${GRAPHIC_CARD}|grep -i 'virtualbox[[:space:]]'` != "" ]];then
        PACKAGES="${PACKAGES} virtualbox-guest-utils virtualbox-guest-modules"
    fi

    if [[ `echo ${GRAPHIC_CARD}|grep -i 'vmware[[:space:]]'` != "" ]];then
        PACKAGES="${PACKAGES} xf86-video-vmware"
    fi

    if [[ `echo ${GRAPHIC_CARD}|grep -i 'via[[:space:]]'` != "" ]];then
        PACKAGES="${PACKAGES} xf86-video-openchrome"
    fi



    if [[ `echo ${WLAN_CARD}|grep -i broadcom` != "" ]];then
        PACKAGES="${PACKAGES} broadcom-wl"
    fi



    if [[ -e /var/state/dhcp/dhclient.leases ]]; then
        ! [[ "$(echo ${PACKAGES} | grep -w dhclient)" ]] && PACKAGES="${PACKAGES} dhclient"
    fi
    # Add filesystem packages
    if [[ "$(${_BLKID} -o value -s TYPE | grep ntfs)" ]]; then
        ! [[ "$(echo ${PACKAGES} | grep -w ntfs-3g)" ]] && PACKAGES="${PACKAGES} ntfs-3g"
    fi
    if [[ "$(${_BLKID} -o value -s TYPE | grep btrfs)" ]]; then
        ! [[ "$(echo ${PACKAGES} | grep -w btrfs-progs)" ]] && PACKAGES="${PACKAGES} btrfs-progs"
    fi
    if [[ "$(${_BLKID} -o value -s TYPE | grep nilfs2)" ]]; then
        ! [[ "$(echo ${PACKAGES} | grep -w nilfs-utils)" ]] && PACKAGES="${PACKAGES} nilfs-utils"
    fi
    if [[ "$(${_BLKID} -o value -s TYPE | grep ext)" ]]; then
        ! [[ "$(echo ${PACKAGES} | grep -w e2fsprogs)" ]] && PACKAGES="${PACKAGES} e2fsprogs"
    fi
    if [[ "$(${_BLKID} -o value -s TYPE | grep reiserfs)" ]]; then
        ! [[ "$(echo ${PACKAGES} | grep -w reiserfsprogs)" ]] && PACKAGES="${PACKAGES} reiserfsprogs"
    fi
    if [[ "$(${_BLKID} -o value -s TYPE | grep xfs)" ]]; then
        ! [[ "$(echo ${PACKAGES} | grep -w xfsprogs)" ]] && PACKAGES="${PACKAGES} xfsprogs"
    fi
    if [[ "$(${_BLKID} -o value -s TYPE | grep jfs)" ]]; then
        ! [[ "$(echo ${PACKAGES} | grep -w jfsutils)" ]] && PACKAGES="${PACKAGES} jfsutils"
    fi
    if [[ "$(${_BLKID} -o value -s TYPE | grep vfat)" ]]; then
        ! [[ "$(echo ${PACKAGES} | grep -w dosfstools)" ]] && PACKAGES="${PACKAGES} dosfstools"
    fi
    if ! [[ "$(dmraid_devices)" = "" ]]; then
        ! [[ "$(echo ${PACKAGES} | grep -w dmraid)" ]] && PACKAGES="${PACKAGES} dmraid"
    fi

    # Install chinese fonts
    if [ "$LOCALE" = 'zh_TW' ] || [ "$LOCALE" = 'zh_CN' ];then
        PACKAGES="${PACKAGES} opendesktop-fonts"
    fi

    NEXTITEM="4"
    S_SELECT=1
    install_packages


}


# install_packages()
# performs package installation to the target system
#
install_packages() {
    destdir_mounts || return 1
    if [[ "${MODE}" = "media" ]]; then
        if [[ "${PACKAGES}" = "" || "${S_SELECT}" != "1" ]]; then
            DIALOG --msgbox "Error:\nYou have to select packages first." 0 0
            select_packages || return 1
        fi
    else
        if [[ "${S_SELECT}" != "1" ]]; then
            DIALOG --msgbox "Error:\nYou have to select packages first." 0 0
            select_packages || return 1
        fi
    fi
    if [[ "${S_MKFS}" != "1" && "${S_MKFSAUTO}" != "1" ]]; then
        getdest
    fi
    DIALOG --msgbox $"Package installation will begin now.  You can watch the output in the progress window. Please be patient." 0 0
    run_pacman
    S_INSTALL=1
    NEXTITEM="4"
    chroot_mount
    # automagic time!
    # any automatic configuration should go here


    DIALOG --infobox $"Writing base configuration..." 6 40
    auto_addons
    auto_fstab
    auto_mdadm
    auto_luks
    # tear down the chroot environment
    chroot_umount
}

# add archboot addons if activated
auto_addons()
{
    if [[ -d /tmp/packages ]]; then
        DO_ADDON=""
        DIALOG --yesno "Would you like to install your addons packages to installed system?" 0 0 && DO_ADDON="yes"
        if [[ "${DO_ADDON}" = "yes" ]]; then
            DIALOG --infobox "Installing the addons packages..." 0 0
            ${PACMAN} -U /tmp/packages/* 2>&1 >> /tmp/pacman.log
        fi
    fi
}

# auto_fstab()
# preprocess fstab file
# comments out old fields and inserts new ones
# according to partitioning/formatting stage
#
auto_fstab(){
    # Modify fstab
    if [[ "${S_MKFS}" = "1" || "${S_MKFSAUTO}" = "1" ]]; then
        if [[ -f /tmp/.device-names ]]; then
            sort /tmp/.device-names >>${DESTDIR}/etc/fstab
        fi
        if [[ -f /tmp/.fstab ]]; then
            # clean fstab first from /dev entries
            sed -i -e '/^\/dev/d' ${DESTDIR}/etc/fstab
            sort /tmp/.fstab >>${DESTDIR}/etc/fstab
        fi
    fi
}

# auto_mdadm()
# add mdadm setup to existing /etc/mdadm.conf
auto_mdadm()
{
    if [[ -e ${DESTDIR}/etc/mdadm.conf ]];then
        if [[ -e /proc/mdstat ]];then
            if [[ "$(cat /proc/mdstat | grep ^md)" ]]; then
                DIALOG --infobox $"Adding raid setup to ${DESTDIR}/etc/mdadm.conf ..." 4 40
                mdadm -Ds >> ${DESTDIR}/etc/mdadm.conf
            fi
        fi
    fi
}


getrootfstype() {
    ROOTFS="$(getfstype ${PART_ROOT})"
}

getrootflags() {
    # remove rw for all filesystems and gcpid for nilfs2
    ROOTFLAGS=""
    ROOTFLAGS="$(findmnt -m -n -o options -T ${DESTDIR} | sed -e 's/^rw//g' -e 's/,gcpid=.*[0-9]//g')"
    [[ -n "${ROOTFLAGS}" ]] && ROOTFLAGS="rootflags=${ROOTFLAGS}"
}

getraidarrays() {
    RAIDARRAYS=""
    if ! [[ "$(grep ^ARRAY ${DESTDIR}/etc/mdadm.conf)" ]]; then
        RAIDARRAYS="$(echo -n $(cat /proc/mdstat 2>/dev/null | grep ^md | sed -e 's#\[[0-9]\]##g' -e 's# :.* raid[0-9]##g' -e 's#md#md=#g' -e 's# #,/dev/#g' -e 's#_##g'))"
    fi
}

getcryptsetup() {
    CRYPTSETUP=""
    if ! [[ "$(cryptsetup status $(basename ${PART_ROOT}) | grep inactive)" ]]; then
        #avoid clash with dmraid here
        if [[ "$(cryptsetup status $(basename ${PART_ROOT}))" ]]; then
            if [[ "${NAME_SCHEME_PARAMETER}" == "FSUUID" ]]; then
                CRYPTDEVICE="/dev/disk/by-uuid/$(echo $(${_BLKID} -p -i -s UUID -o value $(cryptsetup status $(basename ${PART_ROOT}) | grep device: | sed -e 's#device:##g')))"
            elif [[ "${NAME_SCHEME_PARAMETER}" == "FSLABEL" ]]; then
                CRYPTDEVICE="/dev/disk/by-label/$(echo $(${_BLKID} -p -i -s LABEL -o value $(cryptsetup status $(basename ${PART_ROOT}) | grep device: | sed -e 's#device:##g')))"
            else
                CRYPTDEVICE="$(echo $(cryptsetup status $(basename ${PART_ROOT}) | grep device: | sed -e 's#device:##g'))"    
            fi
            CRYPTNAME="$(basename ${PART_ROOT})"
            CRYPTSETUP="cryptdevice=${CRYPTDEVICE}:${CRYPTNAME}"
        fi
    fi
}

getrootpartuuid() {
    _rootpart="${PART_ROOT}"
    _partuuid="$(getpartuuid ${PART_ROOT})"
    if [[ -n "${_partuuid}" ]]; then
        _rootpart="PARTUUID=${_partuuid}"
    fi
}

getrootpartlabel() {
    _rootpart="${PART_ROOT}"
    _partlabel="$(getpartlabel ${PART_ROOT})"
    if [[ -n "${_partlabel}" ]]; then
        _rootpart="PARTLABEL=${_partlabel}"
    fi
}

getrootfsuuid() {
    _rootpart="${PART_ROOT}"
    _fsuuid="$(getfsuuid ${PART_ROOT})"
    if [[ -n "${_fsuuid}" ]]; then
        _rootpart="/dev/disk/by-uuid/${_fsuuid}"
    fi
}

getrootfslabel() {
    _rootpart="${PART_ROOT}"
    _fslabel="$(getfslabel ${PART_ROOT})"
    if [[ -n "${_fslabel}" ]]; then
        _rootpart="/dev/disk/by-label/${_fslabel}"
    fi
}

# basic checks needed for all bootloaders
common_bootloader_checks() {
    activate_special_devices
    getrootfstype
    getraidarrays
    getcryptsetup
    getrootflags

    if [[ "${GUID_DETECTED}" == "1" ]]; then
        [[ "${NAME_SCHEME_PARAMETER}" == "PARTUUID" ]] && getrootpartuuid
        [[ "${NAME_SCHEME_PARAMETER}" == "PARTLABEL" ]] && getrootpartlabel
    fi
    
    [[ "${NAME_SCHEME_PARAMETER}" == "FSUUID" ]] && getrootfsuuid
    [[ "${NAME_SCHEME_PARAMETER}" == "FSLABEL" ]] && getrootfslabel
}

# look for a separately-mounted /boot partition
check_bootpart() {
    subdir=""
    bootdev="$(mount | grep "${DESTDIR}/boot " | cut -d' ' -f 1)"
    if [[ "${bootdev}" == "" ]]; then
        subdir="/boot"
        bootdev="${PART_ROOT}"
    fi
}

# check for btrfs bootpart and abort if detected
abort_btrfs_bootpart() {
        FSTYPE="$(${_BLKID} -p -i ${bootdev} -o value -s TYPE)"
        if [[ "${FSTYPE}" = "btrfs" ]]; then
            DIALOG --msgbox $"Error:\nYour selected bootloader cannot boot from btrfs partition with /boot on it." 0 0
            return 1
        fi
}

# check for nilfs2 bootpart and abort if detected
abort_nilfs_bootpart() {
        FSTYPE="$(${_BLKID} -p -i ${bootdev} -o value -s TYPE)"
        if [[ "${FSTYPE}" = "nilfs2" ]]; then
            DIALOG --msgbox $"Error:\nYour selected bootloader cannot boot from nilfs2 partition with /boot on it." 0 0
            return 1
        fi
}

do_uefi_common() {
    
    DISC="$(df -T "${DESTDIR}/boot" | tail -n +2 | awk '{print $1}' | sed 's/\(.\{8\}\).*/\1/')"
    
    if [[ "${DISC}" != "" ]]; then
        CHECK_UEFISYS_PART="1"
        CHECK_BIOS_BOOT_GRUB=""
        RUN_CGDISK=""
        # check_gpt
        check_uefisyspart
    fi
    
    PACKAGES="dosfstools efibootmgr"
    run_pacman
    PACKAGES=""
    
}

do_uefi_x86_64() {
    
    export UEFI_ARCH="x86_64"
    export SPEC_UEFI_ARCH="x64"
    
    do_uefi_common
    
}

do_uefi_i386() {
    
    export UEFI_ARCH="i386"
    export SPEC_UEFI_ARCH="ia32"
    
    do_uefi_common
    
}

do_uefi_efibootmgr() {
    
    modprobe -q efivars
    
    if [[ "$(lsmod | grep ^efivars)" ]]; then
        chroot_mount
        
        if [[ -d "${DESTDIR}/sys/firmware/efi/vars" ]]; then
            cat << EFIBEOF > "${DESTDIR}/efibootmgr_run.sh"
#!/usr/bin/env bash

for _bootnum in \$(efibootmgr | grep '^Boot[0-9]' | fgrep -i '${_EFIBOOTMGR_LABEL}' | cut -b5-8) ; do
    efibootmgr --bootnum "\${_bootnum}" --delete-bootnum
done

echo
efibootmgr --verbose --create --gpt --disk "${_EFIBOOTMGR_DISC}" --part "${_EFIBOOTMGR_PART_NUM}" --write-signature --label '${_EFIBOOTMGR_LABEL}' --loader '\\EFI\\${_EFIBOOTMGR_LOADER_DIR}\\${_EFIBOOTMGR_LOADER_FILE}'
echo

EFIBEOF
            
            chmod a+x "${DESTDIR}/efibootmgr_run.sh"
            chroot "${DESTDIR}" "/bin/bash" "/efibootmgr_run.sh" &>"/tmp/efibootmgr_run.log"
            mv "${DESTDIR}/efibootmgr_run.sh" "/tmp/efibootmgr_run.sh"
        else
            DIALOG --msgbox $"${DESTDIR}/sys/firmware/efi/vars/ directory not found. Check whether you have booted in UEFI boot mode, manually load efivars kernel module and create a boot entry for ${_EFIBOOTMGR_LABEL} in the UEFI Boot Manager." 0 0
        fi
        
        chroot_umount
    else
        DIALOG --msgbox $"efivars kernel module was not loaded properly. Manually load it and create a boot entry for DISC ${_EFIBOOTMGR_DISC} , PART ${_EFIBOOTMGR_PART_NUM} and LOADER \\EFI\\${_EFIBOOTMGR_LOADER_DIR}\\${_EFIBOOTMGR_LOADER_FILE} , in UEFI Boot Manager using efibootmgr." 0 0
    fi
    
    unset _EFIBOOTMGR_LABEL
    unset _EFIBOOTMGR_DISC
    unset _EFIBOOTMGR_PART_NUM
    unset _EFIBOOTMGR_LOADER_DIR
    unset _EFIBOOTMGR_LOADER_FILE
    
}

do_apple_efi_hfs_bless() {
    
    modprobe -q -r efivars || true
    
    ## Grub upstream bzr mactel branch => http://bzr.savannah.gnu.org/lh/grub/branches/mactel/changes
    ## Fedora's mactel-boot => https://bugzilla.redhat.com/show_bug.cgi?id=755093
    DIALOG --msgbox $"TODO: Apple Mac EFI Bootloader Setup" 0 0
    
}

do_uefi_bootmgr_setup() {
    
    _uefisysdev="$(df -T "${DESTDIR}/boot/efi" | tail -n +2 | awk '{print $1}')"
    _DISC="$(echo "${_uefisysdev}" | sed 's/\(.\{8\}\).*/\1/')"
    UEFISYS_PART_NUM="$(${_BLKID} -p -i -s PART_ENTRY_NUMBER -o value "${_uefisysdev}")"
    
    _BOOTMGR_DISC="${_DISC}"
    _BOOTMGR_PART_NUM="${UEFISYS_PART_NUM}"
    
    if [[ "$(cat "/sys/class/dmi/id/sys_vendor")" == 'Apple Inc.' ]] || [[ "$(cat "/sys/class/dmi/id/sys_vendor")" == 'Apple Computer, Inc.' ]]; then
        do_apple_efi_hfs_bless
    else
        ## For all the non-Mac UEFI systems
        _EFIBOOTMGR_LABEL="${_BOOTMGR_LABEL}"
        _EFIBOOTMGR_DISC="${_BOOTMGR_DISC}"
        _EFIBOOTMGR_PART_NUM="${_BOOTMGR_PART_NUM}"
        _EFIBOOTMGR_LOADER_DIR="${_BOOTMGR_LOADER_DIR}"
        _EFIBOOTMGR_LOADER_FILE="${_BOOTMGR_LOADER_FILE}"
        do_uefi_efibootmgr
    fi
    
    unset _BOOTMGR_LABEL
    unset _BOOTMGR_DISC
    unset _BOOTMGR_PART_NUM
    unset _BOOTMGR_LOADER_DIR
    unset _BOOTMGR_LOADER_FILE
    
}

doefistub_uefi_common() {
    
    [[ "$(uname -m)" == "x86_64" ]] && __CARCH="x86_64"
    [[ "$(uname -m)" == "i686" ]] && __CARCH="i386"
    
    if [[ "${__CARCH}" != "${_UEFI_ARCH}" ]]; then
        DIALOG --msgbox $"EFISTUB requires Kernel and UEFI arch to match, and requires CONFIG_EFI_STUB enabled kernel. Please install matching ARCH Kernel and try again." 0 0
    elif [[ "${KERNELPKG}" == "linux-lts" ]]; then
        PACKAGES="efilinux-efi"
        run_pacman
        PACKAGES=""
        
        mkdir -p "${DESTDIR}/boot/efi/EFI/efilinux/"
        cp -f "${DESTDIR}/usr/lib/efilinux/efilinux${_SPEC_UEFI_ARCH}.efi" "${DESTDIR}/boot/efi/EFI/efilinux/efilinux${_SPEC_UEFI_ARCH}.efi"
        
        _EFILINUX="1"
        _CONTINUE="1"
    else
        _CONTINUE="1"
    fi
    
    if [[ "${_CONTINUE}" == "1" ]]; then
        bootdev=""
        grubdev=""
        complexuuid=""
        FAIL_COMPLEX=""
        USE_DMRAID=""
        RAID_ON_LVM=""
        common_bootloader_checks
        
        _EFISTUB_KERNEL="${VMLINUZ/linux/arch}.efi"
        [[ "${_EFILINUX}" == "1" ]] && _EFISTUB_KERNEL="${VMLINUZ/linux/arch}"
        _EFISTUB_INITRAMFS="${INITRAMFS/linux/arch}"
        
        mkdir -p "${DESTDIR}/boot/efi/EFI/arch/"
        
        rm -f "${DESTDIR}/boot/efi/EFI/arch/${_EFISTUB_KERNEL}"
        rm -f "${DESTDIR}/boot/efi/EFI/arch/${_EFISTUB_INITRAMFS}.img"
        rm -f "${DESTDIR}/boot/efi/EFI/arch/${_EFISTUB_INITRAMFS}-fallback.img"
        
        cp -f "${DESTDIR}/boot/${VMLINUZ}" "${DESTDIR}/boot/efi/EFI/arch/${_EFISTUB_KERNEL}"
        cp -f "${DESTDIR}/boot/${INITRAMFS}.img" "${DESTDIR}/boot/efi/EFI/arch/${_EFISTUB_INITRAMFS}.img"
        cp -f "${DESTDIR}/boot/${INITRAMFS}-fallback.img" "${DESTDIR}/boot/efi/EFI/arch/${_EFISTUB_INITRAMFS}-fallback.img"
        
        #######################
        
        cat << CONFEOF > "${DESTDIR}/etc/systemd/system/efistub_copy.path"
[Unit]
Description=Copy EFISTUB Kernel and Initramfs to UEFISYS Partition

[Path]
PathChanged=/boot/${INITRAMFS}-fallback.img
Unit=efistub_copy.service

[Install]
WantedBy=multi-user.target
CONFEOF
        
        cat << CONFEOF > "${DESTDIR}/etc/systemd/system/efistub_copy.service"
[Unit]
Description=Copy EFISTUB Kernel and Initramfs to UEFISYS Partition

[Service]
Type=oneshot
ExecStart=/bin/cp -f /boot/${VMLINUZ} /boot/efi/EFI/arch/${_EFISTUB_KERNEL}
ExecStart=/bin/cp -f /boot/${INITRAMFS}.img /boot/efi/EFI/arch/${_EFISTUB_INITRAMFS}.img
ExecStart=/bin/cp -f /boot/${INITRAMFS}-fallback.img /boot/efi/EFI/arch/${_EFISTUB_INITRAMFS}-fallback.img
CONFEOF
        
        chroot "${DESTDIR}" /usr/bin/systemctl enable efistub_copy.path
        
        if [[ "${INITSCRIPTS}" = "1" ]]; then
            PACKAGES="incron"
            run_pacman
            PACKAGES=""
            
            cat << CONFEOF > "${DESTDIR}/usr/local/bin/efistub_copy.sh"
/bin/cp -f /boot/${VMLINUZ} /boot/efi/EFI/arch/${_EFISTUB_KERNEL}
/bin/cp -f /boot/${INITRAMFS}.img /boot/efi/EFI/arch/${_EFISTUB_INITRAMFS}.img
/bin/cp -f /boot/${INITRAMFS}-fallback.img /boot/efi/EFI/arch/${_EFISTUB_INITRAMFS}-fallback.img
CONFEOF
            
            cat << CONFEOF > "${DESTDIR}/etc/incron.d/efistub_copy.conf"
/boot/${INITRAMFS}-fallback.img IN_CLOSE_WRITE /usr/local/bin/efistub_copy.sh
CONFEOF
            
            DIALOG --msgbox "Add incrond to the DAEMONS list in /etc/rc.conf ." 0 0
        fi
        
        ###########################
        
        _bootdev="$(df -T "${DESTDIR}/boot" | tail -n +2 | awk '{print $1}')"
        _rootdev="$(df -T "${DESTDIR}/" | tail -n +2 | awk '{print $1}')"
        _uefisysdev="$(df -T "${DESTDIR}/boot/efi" | tail -n +2 | awk '{print $1}')"
        
        ROOT_PART_FS_UUID="$(getfsuuid "${_rootdev}")"
        ROOT_PART_FS_LABEL="$(getfslabel "${_rootdev}")"
        ROOT_PART_GPT_GUID="$(getpartuuid "${_rootdev}")"
        ROOT_PART_GPT_LABEL="$(getpartlabel "${_rootdev}")"
        
        getrootfstype
        
        UEFISYS_PART_FS_UUID="$(getfsuuid "${_uefisysdev}")"
        UEFISYS_PART_FS_LABEL="$(getfslabel "${_uefisysdev}")"
        UEFISYS_PART_GPT_GUID="$(getpartuuid "${_uefisysdev}")"
        UEFISYS_PART_GPT_LABEL="$(getpartlabel "${_uefisysdev}")"
        
        [[ "${NAME_SCHEME_PARAMETER}" == "FSUUID" ]] && _rootpart="UUID=${ROOT_PART_FS_UUID}"
        [[ "${NAME_SCHEME_PARAMETER}" == "PARTUUID" ]] && _rootpart="PARTUUID=${ROOT_PART_GPT_GUID}"
        [[ "${NAME_SCHEME_PARAMETER}" == "FSLABEL" ]] && _rootpart="LABEL=${ROOT_PART_FS_LABEL}"
        [[ "${NAME_SCHEME_PARAMETER}" == "PARTLABEL" ]] && _rootpart="PARTLABEL=${ROOT_PART_GPT_LABEL}"
        [[ "${_rootpart}" == "" ]] && _rootpart="${_rootdev}"
        
        ## TODO: All complex stuff like dmraid, cyptsetup etc. for kernel parameters - common_bootloader_checks ?
        _PARAMETERS_UNMOD="root=${_rootpart} ${ROOTFLAGS} rootfstype=${ROOTFS} ${RAIDARRAYS} ${CRYPTSETUP} ro pci=nocrs add_efi_memmap initrd=\\EFI\\arch\\${_EFISTUB_INITRAMFS}.img"
        _PARAMETERS_MOD=$(echo "${_PARAMETERS_UNMOD}" | sed -e 's#   # #g' | sed -e 's#  # #g')
        
        if [[ "${_EFILINUX}" == "1" ]]; then
            cat << CONFEOF > "${DESTDIR}/boot/efi/EFI/efilinux/efilinux.cfg"
-f \\EFI\\arch\\${_EFISTUB_KERNEL} ${_PARAMETERS_MOD} initrd=\\EFI\\arch\\${_EFISTUB_INITRAMFS}-fallback.img
CONFEOF
        fi
        
        # cat << CONFEOF > "${DESTDIR}/boot/efi/EFI/arch/linux.conf"
# ${_PARAMETERS_MOD}
# CONFEOF
        
        ###################################
        
        if [[ -e "${DESTDIR}/boot/efi/EFI/arch/${_EFISTUB_KERNEL}" ]] && [[ -e "${DESTDIR}/boot/efi/EFI/arch/${_EFISTUB_INITRAMFS}.img" ]]; then
            DIALOG --msgbox $"The EFISTUB Kernel and initramfs have been copied to /boot/efi/EFI/arch/${_EFISTUB_KERNEL} and /boot/efi/EFI/arch/${_EFISTUB_INITRAMFS}.img respectively." 0 0
            
            if [[ "${_EFILINUX}" == "1" ]]; then
                DIALOG --msgbox $"You will now be put into the editor to edit efilinux.cfg . After you save your changes, exit the editor." 0 0
                geteditor || return 1
                "${EDITOR}" "${DESTDIR}/boot/efi/EFI/efilinux/efilinux.cfg"
            # else
                # _BOOTMGR_LABEL="Arch Linux (EFISTUB)"
                # _BOOTMGR_LOADER_DIR="arch"
                # _BOOTMGR_LOADER_FILE="${_EFISTUB_KERNEL}"
                # do_uefi_bootmgr_setup
                
                # DIALOG --msgbox "You will now be put into the editor to edit linux.conf . After you save your changes, exit the editor." 0 0
                # geteditor || return 1
             
                # "${EDITOR}" "${DESTDIR}/boot/efi/EFI/arch/linux.conf"
                
                # DIALOG --defaultno --yesno "Do you want to copy /boot/efi/EFI/arch/${_EFISTUB_KERNEL} to /boot/efi/EFI/boot/boot${_SPEC_UEFI_ARCH}.efi .\n\nThis might be needed in some systems where efibootmgr may not work due to firmware issues." 0 0 && _UEFISYS_EFI_BOOT_DIR="1"
                
                # if [[ "${_UEFISYS_EFI_BOOT_DIR}" == "1" ]]; then
                    # mkdir -p "${DESTDIR}/boot/efi/EFI/boot"
                    
                    # rm -f "${DESTDIR}/boot/efi/EFI/boot/boot${_SPEC_UEFI_ARCH}.efi"
                    # rm -f "${DESTDIR}/boot/efi/EFI/boot/linux.conf"
                    
                    # cp -f "${DESTDIR}/boot/efi/EFI/arch/${_EFISTUB_KERNEL}" "${DESTDIR}/boot/efi/EFI/boot/boot${_SPEC_UEFI_ARCH}.efi"
                    # cp -f "${DESTDIR}/boot/efi/EFI/boot/linux.conf" "${DESTDIR}/boot/efi/EFI/boot/linux.conf"
                # fi
            fi
            
            DIALOG --menu $"Select which UEFI Boot Manager to install, to provide a menu for EFISTUB kernels?" 13 55 3 \
                "rEFInd_UEFI_${UEFI_ARCH}" "rEFInd ${UEFI_ARCH} UEFI Boot Manager" \
                "GUMMIBOOT_UEFI_${UEFI_ARCH}" "Simple Text Mode ${UEFI_ARCH} UEFI Boot Manager" \
                "NONE" "No Boot Manager" 2>${ANSWER} || CANCEL=1
            case $(cat ${ANSWER}) in
                "GUMMIBOOT_UEFI_${UEFI_ARCH}") dogummiboot_uefi_common ;;
                "rEFInd_UEFI_${UEFI_ARCH}") dorefind_uefi_common ;;
                "NONE") return 0 ;;
            esac
        else
            DIALOG --msgbox $"Error setting up EFISTUB kernel and initramfs in /boot/efi." 0 0
        fi
    fi
    
}

do_efistub_uefi_x86_64() {
    
    do_uefi_x86_64
    
    doefistub_uefi_common
    
}

do_efistub_uefi_i686() {
    
    do_uefi_i386
    
    doefistub_uefi_common
    
}


dogummiboot_uefi_common() {
    
    DIALOG --msgbox $"Setting up gummiboot-efi now ..." 0 0
    
    PACKAGES="gummiboot-efi"
    run_pacman
    PACKAGES=""
    
    mkdir -p "${DESTDIR}/boot/efi/EFI/gummiboot/"
    cp -f "${DESTDIR}/usr/lib/gummiboot/gummiboot${_SPEC_UEFI_ARCH}.efi" "${DESTDIR}/boot/efi/EFI/gummiboot/gummiboot${_SPEC_UEFI_ARCH}.efi"
    
    if [[ "${_EFILINUX}" == "1" ]]; then
        cat << GUMEOF > "${DESTDIR}/boot/efi/loader/entries/cinnarch-core-lts-main.conf"
title    Cinnarch LTS via EFILINUX
efi      /EFI/efilinux/efilinux${_SPEC_UEFI_ARCH}.efi
GUMEOF
        
        cat << GUMEOF > "${DESTDIR}/boot/efi/loader/entries/cinnarch-core-lts-fallback.conf"
title    Cinnarch LTS via EFILINUX - fallback initramfs
efi      /EFI/efilinux/efilinux${_SPEC_UEFI_ARCH}.efi
GUMEOF
        
        cat << GUMEOF > "${DESTDIR}/boot/efi/loader/loader.conf"
timeout 5
default cinnarch-core-lts-main
GUMEOF
        
    else
        cat << GUMEOF > "${DESTDIR}/boot/efi/loader/entries/cinnarch-core-main.conf"
title    Cinnarch
linux    /EFI/arch/${_EFISTUB_KERNEL}
initrd   /EFI/arch/${_EFISTUB_INITRAMFS}.img
options  ${_PARAMETERS_MOD}
GUMEOF
        
        cat << GUMEOF > "${DESTDIR}/boot/efi/loader/entries/cinnarch-core-fallback.conf"
title    Cinnarch fallback initramfs
linux    /EFI/arch/${_EFISTUB_KERNEL}
initrd   /EFI/arch/${_EFISTUB_INITRAMFS}-fallback.img
options  ${_PARAMETERS_MOD}
GUMEOF
        
        cat << GUMEOF > "${DESTDIR}/boot/efi/loader/loader.conf"
timeout 5
default cinnarch-core-main
GUMEOF
        
    fi
    
    if [[ -e "${DESTDIR}/boot/efi/EFIgummiboot/gummiboot${_SPEC_UEFI_ARCH}.efi" ]]; then
        _BOOTMGR_LABEL="Cinnarch (gummiboot)"
        _BOOTMGR_LOADER_DIR="gummiboot"
        _BOOTMGR_LOADER_FILE="gummiboot${_SPEC_UEFI_ARCH}.efi"
        do_uefi_bootmgr_setup
        
        DIALOG --msgbox $"gummiboot-efi has been setup successfully." 0 0
        
        DIALOG --msgbox $"You will now be put into the editor to edit loader.conf and gummiboot menu entry files . After you save your changes, exit the editor." 0 0
        geteditor || return 1
        
        if [[ "${_EFILINUX}" == "1" ]]; then
            "${EDITOR}" "${DESTDIR}/boot/efi/loader/entries/cinnarch-core-lts-main.conf"
            "${EDITOR}" "${DESTDIR}/boot/efi/loader/entries/cinnarch-core-lts-fallback.conf"
        else
            "${EDITOR}" "${DESTDIR}/boot/efi/loader/entries/cinnarch-core-main.conf"
            "${EDITOR}" "${DESTDIR}/boot/efi/loader/entries/cinnarch-core-fallback.conf"
        fi
        
        "${EDITOR}" "${DESTDIR}/boot/efi/loader/loader.conf"
        
        DIALOG --defaultno --yesno $"Do you want to copy /boot/efi/EFI/gummiboot/gummiboot${_SPEC_UEFI_ARCH}.efi to /boot/efi/EFI/boot/boot${_SPEC_UEFI_ARCH}.efi ?\n\nThis might be needed in some systems where efibootmgr may not work due to firmware issues." 0 0 && _UEFISYS_EFI_BOOT_DIR="1"
        
        if [[ "${_UEFISYS_EFI_BOOT_DIR}" == "1" ]]; then
            mkdir -p "${DESTDIR}/boot/efi/EFI/boot"
            rm -f "${DESTDIR}/boot/efi/EFI/boot/boot${_SPEC_UEFI_ARCH}.efi"
            cp -f "${DESTDIR}/boot/efi/EFI/gummiboot/gummiboot${_SPEC_UEFI_ARCH}.efi" "${DESTDIR}/boot/efi/EFI/boot/boot${_SPEC_UEFI_ARCH}.efi"
        fi
    else
        DIALOG --msgbox $"Error setting up gummiboot-efi." 0 0
    fi
    
}


dorefind_uefi_common() {
    
    DIALOG --msgbox $"Setting up refind-efi now ..." 0 0
    
    PACKAGES="refind-efi"
    run_pacman
    PACKAGES=""
    
    mkdir -p "${DESTDIR}/boot/efi/EFI/refind/"
    cp -f "${DESTDIR}/usr/lib/refind/refind${_SPEC_UEFI_ARCH}.efi" "${DESTDIR}/boot/efi/EFI/refind/refind${_SPEC_UEFI_ARCH}.efi"
    cp -r "${DESTDIR}/usr/share/refind/icons" "${DESTDIR}/boot/efi/EFI/refind/icons"
    
    mkdir -p "${DESTDIR}/boot/efi/EFI/tools/"
    cp -rf "${DESTDIR}/usr/lib/refind/drivers_${_SPEC_UEFI_ARCH}" "${DESTDIR}/boot/efi/EFI/tools/drivers_${_SPEC_UEFI_ARCH}"
    
    _REFIND_CONFIG="${DESTDIR}/boot/efi/EFI/refind/refind.conf"
    cp -f "${DESTDIR}/usr/lib/refind/config/refind.conf" "${_REFIND_CONFIG}"

    sed 's|^timeout 20|timeout 5|g' -i "${_REFIND_CONFIG}"
    sed 's|^#hideui singleuser|hideui singleuser|g' -i "${_REFIND_CONFIG}"
    sed 's|^#resolution 1024 768|resolution 1024 768|g' -i "${_REFIND_CONFIG}"
    sed 's|^#use_graphics_for osx,linux|use_graphics_for osx|g' -i "${_REFIND_CONFIG}"
    sed 's|^#showtools shell, about, reboot|showtools shell,about,reboot,shutdown,exit|g' -i "${_REFIND_CONFIG}"
    sed 's|^#scan_driver_dirs EFI/tools/drivers,drivers|scan_driver_dirs EFI/tools/drivers_${_SPEC_UEFI_ARCH}|g' -i "${_REFIND_CONFIG}"
    sed 's|^#scanfor internal,external,optical,manual|scanfor manual,internal,external,optical|g' -i "${_REFIND_CONFIG}"
    sed 's|^#scan_delay 5|scan_delay 1|g' -i "${_REFIND_CONFIG}"
    sed 's|^#also_scan_dirs boot,EFI/linux/kernels|also_scan_dirs boot|g' -i "${_REFIND_CONFIG}"
    sed 's|^#dont_scan_dirs EFI/boot|dont_scan_dirs EFI/boot|g' -i "${_REFIND_CONFIG}"
    sed 's|^#scan_all_linux_kernels|scan_all_linux_kernels|g' -i "${_REFIND_CONFIG}"
    sed 's|^#max_tags 0|max_tags 0|g' -i "${_REFIND_CONFIG}"
    
    if [[ "${_EFILINUX}" == "1" ]]; then
        cat << REFINDEOF >> "${_REFIND_CONFIG}"

menuentry "Cinnarch LTS via EFILINUX" {
    icon /EFI/refind/icons/os_arch.icns
    loader /EFI/efilinux/efilinux${_SPEC_UEFI_ARCH}.efi
}

menuentry "Cinnarch LTS via EFILINUX - fallback initramfs" {
    icon /EFI/refind/icons/os_arch.icns
    loader /EFI/efilinux/efilinux${_SPEC_UEFI_ARCH}.efi
}

REFINDEOF
        
    else
        cat << REFINDEOF > "${DESTDIR}/boot/efi/EFI/arch/refind_linux.conf"
"Boot with Defaults"              "${_PARAMETERS_MOD}"
"Boot with fallback initramfs"    "${_PARAMETERS_MOD} initrd=\\EFI\\arch\\${_EFISTUB_INITRAMFS}-fallback.img"
REFINDEOF
        
    fi
    
    if [[ -e "${DESTDIR}/boot/efi/EFI/refind/refind${_SPEC_UEFI_ARCH}.efi" ]]; then
        _BOOTMGR_LABEL="Cinnarch (rEFInd)"
        _BOOTMGR_LOADER_DIR="refind"
        _BOOTMGR_LOADER_FILE="refind${_SPEC_UEFI_ARCH}.efi"
        do_uefi_bootmgr_setup
        
        DIALOG --msgbox $"refind-efi has been setup successfully." 0 0
        
        DIALOG --msgbox $"You will now be put into the editor to edit refind.conf (and maybe refind_linux.conf) . After you save your changes, exit the editor." 0 0
        geteditor || return 1
        "${EDITOR}" "${_REFIND_CONFIG}"
        [[ "${_EFILINUX}" != "1" ]] && "${EDITOR}" "${DESTDIR}/boot/efi/EFI/arch/refind_linux.conf"
        
        DIALOG --defaultno --yesno $"Do you want to copy /boot/efi/EFI/refind/refind${_SPEC_UEFI_ARCH}.efi to /boot/efi/EFI/boot/boot${_SPEC_UEFI_ARCH}.efi ?\n\nThis might be needed in some systems where efibootmgr may not work due to firmware issues." 0 0 && _UEFISYS_EFI_BOOT_DIR="1"
        
        if [[ "${_UEFISYS_EFI_BOOT_DIR}" == "1" ]]; then
            mkdir -p "${DESTDIR}/boot/efi/EFI/boot"
            
            rm -f "${DESTDIR}/boot/efi/EFI/boot/boot${_SPEC_UEFI_ARCH}.efi"
            rm -f "${DESTDIR}/boot/efi/EFI/boot/refind.conf"
            rm -rf "${DESTDIR}/boot/efi/EFI/boot/icons"
            
            cp -f "${DESTDIR}/boot/efi/EFI/refind/refind${_SPEC_UEFI_ARCH}.efi" "${DESTDIR}/boot/efi/EFI/boot/boot${_SPEC_UEFI_ARCH}.efi"
            cp -f "${_REFIND_CONFIG}" "${DESTDIR}/boot/efi/EFI/boot/refind.conf"
            cp -rf "${DESTDIR}/boot/efi/EFI/refind/icons" "${DESTDIR}/boot/efi/EFI/boot/icons"
        fi
    else
        DIALOG --msgbox $"Error setting up refind-efi." 0 0
    fi
    
}




dogrub_common_before() {
    ##### Check whether the below limitations still continue with ver 2.00~beta4
    ### Grub(2) restrictions:
    # - Encryption is not recommended for grub(2) /boot!
    
    bootdev=""
    grubdev=""
    complexuuid=""
    FAIL_COMPLEX=""
    USE_DMRAID=""
    RAID_ON_LVM=""
    common_bootloader_checks
    
    if ! [[ "$(dmraid -r | grep ^no )" ]]; then
        DIALOG --yesno $"Setup detected dmraid device.\nDo you want to install grub on this device?" 0 0 && USE_DMRAID="1"
    fi
}

dogrub_config() {

    ########
    
    BOOT_PART_FS_UUID="$(LD_LIBRARY_PATH="${DESTDIR}/usr/lib:${DESTDIR}/lib" "${DESTDIR}/usr/sbin/grub-probe" --target="fs_uuid" "${DESTDIR}/boot" 2>/dev/null)"
    BOOT_PART_FS="$(LD_LIBRARY_PATH="${DESTDIR}/usr/lib:${DESTDIR}/lib" "${DESTDIR}/usr/sbin/grub-probe" --target="fs" "${DESTDIR}/boot" 2>/dev/null)"
    
    BOOT_PART_FS_LABEL="$(LD_LIBRARY_PATH="${DESTDIR}/usr/lib:${DESTDIR}/lib" "${DESTDIR}/usr/sbin/grub-probe" --target="fs_label" "${DESTDIR}/boot" 2>/dev/null)"
    BOOT_PART_DRIVE="$(LD_LIBRARY_PATH="${DESTDIR}/usr/lib:${DESTDIR}/lib" "${DESTDIR}/usr/sbin/grub-probe" --target="drive" "${DESTDIR}/boot" 2>/dev/null)"
    
    BOOT_PART_HINTS_STRING="$(LD_LIBRARY_PATH="${DESTDIR}/usr/lib:${DESTDIR}/lib" "${DESTDIR}/usr/sbin/grub-probe" --target="hints_string" "${DESTDIR}/boot" 2>/dev/null)"
    
    ########
    
    ROOT_PART_FS_UUID="$(LD_LIBRARY_PATH="${DESTDIR}/usr/lib:${DESTDIR}/lib" "${DESTDIR}/usr/sbin/grub-probe" --target="fs_uuid" "${DESTDIR}/" 2>/dev/null)"
    ROOT_PART_FS="$(LD_LIBRARY_PATH="${DESTDIR}/usr/lib:${DESTDIR}/lib" "${DESTDIR}/usr/sbin/grub-probe" --target="fs" "${DESTDIR}/" 2>/dev/null)"
    
    ROOT_PART_FS_LABEL="$(LD_LIBRARY_PATH="${DESTDIR}/usr/lib:${DESTDIR}/lib" "${DESTDIR}/usr/sbin/grub-probe" --target="fs_label" "${DESTDIR}/" 2>/dev/null)"
    ROOT_PART_DEVICE="$(LD_LIBRARY_PATH="${DESTDIR}/usr/lib:${DESTDIR}/lib" "${DESTDIR}/usr/sbin/grub-probe" --target="device" "${DESTDIR}/" 2>/dev/null)"
    
    ROOT_PART_HINTS_STRING="$(LD_LIBRARY_PATH="${DESTDIR}/usr/lib:${DESTDIR}/lib" "${DESTDIR}/usr/sbin/grub-probe" --target="hints_string" "${DESTDIR}/" 2>/dev/null)"
    
    ########
    
    USR_PART_FS_UUID="$(LD_LIBRARY_PATH="${DESTDIR}/usr/lib:${DESTDIR}/lib" "${DESTDIR}/usr/sbin/grub-probe" --target="fs_uuid" "${DESTDIR}/usr" 2>/dev/null)"
    USR_PART_FS="$(LD_LIBRARY_PATH="${DESTDIR}/usr/lib:${DESTDIR}/lib" "${DESTDIR}/usr/sbin/grub-probe" --target="fs" "${DESTDIR}/usr" 2>/dev/null)"
    
    USR_PART_FS_LABEL="$(LD_LIBRARY_PATH="${DESTDIR}/usr/lib:${DESTDIR}/lib" "${DESTDIR}/usr/sbin/grub-probe" --target="fs_label" "${DESTDIR}/usr" 2>/dev/null)"
    
    USR_PART_HINTS_STRING="$(LD_LIBRARY_PATH="${DESTDIR}/usr/lib:${DESTDIR}/lib" "${DESTDIR}/usr/sbin/grub-probe" --target="hints_string" "${DESTDIR}/usr" 2>/dev/null)"
    
    ########
    
    if [[ "${GRUB_UEFI}" == "1" ]]; then
        UEFISYS_PART_FS_UUID="$(LD_LIBRARY_PATH="${DESTDIR}/usr/lib:${DESTDIR}/lib" "${DESTDIR}/usr/sbin/grub-probe" --target="fs_uuid" "${DESTDIR}/boot/efi" 2>/dev/null)"
        
        UEFISYS_PART_FS_LABEL="$(LD_LIBRARY_PATH="${DESTDIR}/usr/lib:${DESTDIR}/lib" "${DESTDIR}/usr/sbin/grub-probe" --target="fs_label" "${DESTDIR}/boot/efi" 2>/dev/null)"
        UEFISYS_PART_DRIVE="$(LD_LIBRARY_PATH="${DESTDIR}/usr/lib:${DESTDIR}/lib" "${DESTDIR}/usr/sbin/grub-probe" --target="drive" "${DESTDIR}/boot/efi" 2>/dev/null)"
        
        UEFISYS_PART_HINTS_STRING="$(LD_LIBRARY_PATH="${DESTDIR}/usr/lib:${DESTDIR}/lib" "${DESTDIR}/usr/sbin/grub-probe" --target="hints_string" "${DESTDIR}/boot/efi" 2>/dev/null)"
    fi
    
    ########
    
    ## udev 180 onwards
    if [[ "$(${_BLKID} -p -i  -o value -s PART_ENTRY_SCHEME ${ROOT_PART_DEVICE})" == 'gpt' ]]; then
        ROOT_PART_GPT_GUID="$(${_BLKID} -p -i -o value -s PART_ENTRY_UUID ${ROOT_PART_DEVICE})"
        ROOT_PART_GPT_LABEL="$(${_BLKID} -p -i -o value -s PART_ENTRY_NAME ${ROOT_PART_DEVICE})"
    fi
    
    ########
    
    if [[ "${ROOT_PART_FS_UUID}" == "${BOOT_PART_FS_UUID}" ]]; then
        subdir="/boot"
    else
        subdir=""
    fi
    
    ########
    
    cp -f "${DESTDIR}/${GRUB_PREFIX_DIR}/grub.cfg" "/tmp/.grub.cfg"
    # remove the default entries by truncating the file at our little tag (set default)
    head -n $(cat /tmp/.grub.cfg | grep -n 'set default' | cut -d: -f 1) "/tmp/.grub.cfg" > "${DESTDIR}/${GRUB_PREFIX_DIR}/grub.cfg"
    rm -f "/tmp/.grub.cfg"
    
    NUMBER="0"
    
    ## Ignore if the insmod entries are repeated - there are possibilities of having /boot in one disk and root-fs in altogether different disk
    ## with totally different configuration.
    
    cat << EOF >> "${DESTDIR}/${GRUB_PREFIX_DIR}/grub.cfg"

if [ "\${grub_platform}" == "efi" ]; then
    set _UEFI_ARCH="\${grub_cpu}"
    
    if [ "\${grub_cpu}" == "x86_64" ]; then
        set _SPEC_UEFI_ARCH="x64"
    fi
    
    if [ "\${grub_cpu}" == "i386" ]; then
        set _SPEC_UEFI_ARCH="ia32"
    fi
fi

EOF
    
    cat << EOF >> "${DESTDIR}/${GRUB_PREFIX_DIR}/grub.cfg"

insmod part_gpt
insmod part_msdos

# Include fat fs module - required for uefi systems.
insmod fat

insmod ${BOOT_PART_FS}
insmod ${ROOT_PART_FS}
insmod ${USR_PART_FS}

insmod search_fs_file
insmod search_fs_uuid
insmod search_label

insmod linux
insmod chain

set pager="1"
# set debug="all"

set locale_dir="\${prefix}/locale"

EOF
    
    [[ "${USE_RAID}" == "1" ]] && echo "insmod raid" >> "${DESTDIR}/${GRUB_PREFIX_DIR}/grub.cfg"
    ! [[ "${RAID_ON_LVM}" == "" ]] && echo "insmod lvm" >> "${DESTDIR}/${GRUB_PREFIX_DIR}/grub.cfg"
    
    cat << EOF >> "${DESTDIR}/${GRUB_PREFIX_DIR}/grub.cfg"

if [ -e "\${prefix}/\${grub_cpu}-\${grub_platform}/all_video.mod" ]; then
    insmod all_video
else
    if [ "\${grub_platform}" == "efi" ]; then
        insmod efi_gop
        insmod efi_uga
    fi
    
    if [ "\${grub_platform}" == "pc" ]; then
        insmod vbe
        insmod vga
    fi
    
    insmod video_bochs
    insmod video_cirrus
fi

insmod font

search --fs-uuid --no-floppy --set=usr_part ${USR_PART_HINTS_STRING} ${USR_PART_FS_UUID}
search --fs-uuid --no-floppy --set=root_part ${ROOT_PART_HINTS_STRING} ${ROOT_PART_FS_UUID}

if [ -e "(\${usr_part})/share/grub/unicode.pf2" ]; then
    set _fontfile="(\${usr_part})/share/grub/unicode.pf2"
else
    if [ -e "(\${root_part})/usr/share/grub/unicode.pf2" ]; then
        set _fontfile="(\${root_part})/usr/share/grub/unicode.pf2"
    else
        if [ -e "\${prefix}/fonts/unicode.pf2" ]; then
            set _fontfile="\${prefix}/fonts/unicode.pf2"
        fi
    fi
fi

if loadfont "\${_fontfile}" ; then
    insmod gfxterm
    set gfxmode="auto"
    
    terminal_input console
    terminal_output gfxterm
fi

EOF
    
    echo "" >> "${DESTDIR}/${GRUB_PREFIX_DIR}/grub.cfg"
    sort "/tmp/.device-names" >> "${DESTDIR}/${GRUB_PREFIX_DIR}/grub.cfg"
    echo "" >> "${DESTDIR}/${GRUB_PREFIX_DIR}/grub.cfg"
    
    if [[ "${NAME_SCHEME_PARAMETER}" == "FSUUID" ]]; then
        GRUB_ROOT_DRIVE="search --fs-uuid --no-floppy --set=root ${BOOT_PART_HINTS_STRING} ${BOOT_PART_FS_UUID}"
        _rootpart="UUID=${ROOT_PART_FS_UUID}"
        
    elif [[ "${NAME_SCHEME_PARAMETER}" == "PARTUUID" ]]; then
        GRUB_ROOT_DRIVE="search --fs-uuid --no-floppy --set=root ${BOOT_PART_HINTS_STRING} ${BOOT_PART_FS_UUID}" # GRUB(2) does not yet support PARTUUID
        _rootpart="/dev/disk/by-partuuid/${ROOT_PART_GPT_GUID}"
        
    elif [[ "${NAME_SCHEME_PARAMETER}" == "FSLABEL" ]]; then
        GRUB_ROOT_DRIVE="search --label --no-floppy --set=root ${BOOT_PART_HINTS_STRING} ${BOOT_PART_FS_LABEL}"
        _rootpart="LABEL=${ROOT_PART_FS_LABEL}"
        
    elif [[ "${NAME_SCHEME_PARAMETER}" == "PARTLABEL" ]]; then
        GRUB_ROOT_DRIVE="search --label --no-floppy --set=root ${BOOT_PART_HINTS_STRING} ${BOOT_PART_FS_LABEL}" # GRUB(2) does not yet support PARTLABEL
        _rootpart="/dev/disk/by-partlabel/${ROOT_PART_GPT_LABEL}"
        
    else
        GRUB_ROOT_DRIVE="set root="${BOOT_PART_DRIVE}""
        _rootpart="${ROOT_PART_DEVICE}"
        
    fi
    
    # fallback to device if no label or uuid can be detected, eg. luks device
    if [[ -z "${ROOT_PART_FS_UUID}" ]] && [[ -z "${ROOT_PART_FS_LABEL}" ]]; then
        _rootpart="${ROOT_PART_DEVICE}"
    fi
    
    LINUX_UNMOD_COMMAND="linux ${subdir}/${VMLINUZ} root=${_rootpart} ${ROOTFLAGS} rootfstype=${ROOTFS} ${RAIDARRAYS} ${CRYPTSETUP} ro"
    LINUX_MOD_COMMAND=$(echo "${LINUX_UNMOD_COMMAND}" | sed -e 's#   # #g' | sed -e 's#  # #g')
    
    ## create default kernel entry
    cat << EOF >> "${DESTDIR}/${GRUB_PREFIX_DIR}/grub.cfg"

# (${NUMBER}) Cinnarch
menuentry "Cinnarch" {
    set gfxpayload="keep"
    ${GRUB_ROOT_DRIVE}
    ${LINUX_MOD_COMMAND}
    initrd ${subdir}/${INITRAMFS}.img
}

EOF
    
    NUMBER=$((${NUMBER}+1))
    
    ## create kernel fallback entry
    cat << EOF >> "${DESTDIR}/${GRUB_PREFIX_DIR}/grub.cfg"

# (${NUMBER}) Cinnarch Fallback
menuentry "Cinnarch Fallback" {
    set gfxpayload="keep"
    ${GRUB_ROOT_DRIVE}
    ${LINUX_MOD_COMMAND}
    initrd ${subdir}/${INITRAMFS}-fallback.img
}

EOF
    
    NUMBER=$((${NUMBER}+1))
    
    cat << EOF >> "${DESTDIR}/${GRUB_PREFIX_DIR}/grub.cfg"

if [ "\${grub_platform}" == "efi" ]; then
    
    ## UEFI Shell 2.0
    ## Will work only in grub(2) uefi
    #menuentry "UEFI \${_UEFI_ARCH} Shell 2.0 - For Spec. Ver. >=2.3 systems" {
    #    search --fs-uuid --no-floppy --set=root ${UEFISYS_PART_HINTS_STRING} ${UEFISYS_PART_FS_UUID}
    #    chainloader /efi/tools/shell\${_SPEC_UEFI_ARCH}.efi
    #}
    
    ## UEFI Shell 1.0
    ## Will work only in grub(2) uefi
    #menuentry "UEFI \${_UEFI_ARCH} Shell 1.0 - For Spec. Ver. <2.3 systems" {
    #    search --fs-uuid --no-floppy --set=root ${UEFISYS_PART_HINTS_STRING} ${UEFISYS_PART_FS_UUID}
    #    chainloader /efi/tools/shell\${_SPEC_UEFI_ARCH}_old.efi
    #}
    
fi

EOF
    
    NUMBER=$((${NUMBER}+1))
    
    cat << EOF >> "${DESTDIR}/${GRUB_PREFIX_DIR}/grub.cfg"

if [ "\${grub_platform}" == "efi" ]; then
    
    ## Windows x86_64 UEFI
    ## Will work only in grub(2) uefi x86_64
    #menuentry \"Microsoft Windows x86_64 UEFI-GPT\" {
    #    insmod part_gpt
    #    insmod fat
    #    insmod search_fs_uuid
    #    insmod chain
    #    search --fs-uuid --no-floppy --set=root ${UEFISYS_PART_HINTS_STRING} ${UEFISYS_PART_FS_UUID}
    #    chainloader /efi/Microsoft/Boot/bootmgfw.efi
    #}
    
fi

EOF
    
    NUMBER=$((${NUMBER}+1))
    
    ## TODO: Detect actual Windows installation if any
    ## create example file for windows
    cat << EOF >> "${DESTDIR}/${GRUB_PREFIX_DIR}/grub.cfg"

if [ "\${grub_platform}" == "pc" ]; then
    
    ## Windows BIOS
    ## Will work only in grub(2) bios
    #menuentry \"Microsoft Windows 7 BIOS-MBR\" {
    #    insmod part_msdos
    #    insmod ntfs
    #    insmod search_fs_uuid
    #    insmod ntldr
    #    search --fs-uuid --no-floppy --set=root 69B235F6749E84CE
    #    ntldr /bootmgr
    #}
    
fi

EOF
    
    ## copy unicode.pf2 font file
    cp -f "${DESTDIR}/usr/share/grub/unicode.pf2" "${DESTDIR}/${GRUB_PREFIX_DIR}/fonts/unicode.pf2"
    
    ## Edit grub.cfg config file
    # DIALOG --msgbox "You must now review the grub(2) configuration file.\n\nYou will now be put into the editor. After you save your changes, exit the editor." 0 0
    # geteditor || return 1
    # "${EDITOR}" "${DESTDIR}/${GRUB_PREFIX_DIR}/grub.cfg"

    
    unset BOOT_PART_FS_UUID
    unset BOOT_PART_FS
    unset BOOT_PART_FS_LABEL
    unset BOOT_PART_DRIVE
    
    unset ROOT_PART_FS_UUID
    unset ROOT_PART_FS
    unset ROOT_PART_FS_LABEL
    unset ROOT_PART_DEVICE
    
    unset GRUB_ROOT_DRIVE
    unset LINUX_UNMOD_COMMAND
    unset LINUX_MOD_COMMAND
    
    
}

dogrub_bios() {
    
    dogrub_common_before

    PACKAGES="grub-common grub-bios os-prober"
    run_pacman
    # reset PACKAGES after installing
    PACKAGES=""

    
    # try to auto-configure GRUB(2)...
    if [[ "${PART_ROOT}" != "" ]]; then
        check_bootpart
        
        # check if raid, raid partition, dmraid or device devicemapper is used
        if [[ "$(echo ${bootdev} | grep /dev/md)" ]] || [[ "$(echo ${bootdev} | grep /dev/mapper)" ]]; then
            # boot from lvm, raid, partitioned raid and dmraid devices is supported
            FAIL_COMPLEX="0"
            
            if [[ "$(cryptsetup status ${bootdev})" ]]; then
                # encryption devices are not supported
                FAIL_COMPLEX="1"
            fi
        fi
        
        if [[ "${FAIL_COMPLEX}" == "0" ]]; then
            grubdev=$(basename ${bootdev})
            complexuuid=$(getfsuuid ${bootdev})
            # check if mapper is used
            if  [[ "$(echo ${bootdev} | grep /dev/mapper)" ]]; then
                RAID_ON_LVM="0"
                
                #check if mapper contains a md device!
                for devpath in $(pvs -o pv_name --noheading); do
                    if [[ "$(echo ${devpath} | grep -v /dev/md*p | grep /dev/md)" ]]; then
                        detectedvolumegroup="$(echo $(pvs -o vg_name --noheading ${devpath}))"
                        
                        if [[ "$(echo /dev/mapper/${detectedvolumegroup}-* | grep ${bootdev})" ]]; then
                            # change bootdev to md device!
                            bootdev=$(pvs -o pv_name --noheading ${devpath})
                            RAID_ON_LVM="1"
                            break
                        fi
                    fi
                done
            fi
            
            #check if raid is used
            USE_RAID=""
            if [[ "$(echo ${bootdev} | grep /dev/md)" ]]; then
                USE_RAID="1"
            fi
        else
            # use normal device
            grubdev=$(mapdev ${bootdev})
        fi
    fi
    
    
    # A switch is needed if complex ${bootdev} is used!
    # - LVM and RAID ${bootdev} needs the MBR of a device and cannot be used itself as ${bootdev}
    if [[ "${FAIL_COMPLEX}" == "0" ]]; then
        DEVS="$(findbootloaderdisks _)"
        
        if [[ "${DEVS}" == "" ]]; then
            DIALOG --msgbox $"No hard drives were found" 0 0
            return 1
        fi
        
        DIALOG --menu $"Select the boot device where the GRUB(2) bootloader will be installed." 14 55 7 ${DEVS} 2>${ANSWER} || return 1
        bootdev=$(cat ${ANSWER})
    else
        DEVS="$(findbootloaderdisks _)"
        
        ## grub-bios install to partition is not supported
        # DEVS="${DEVS} $(findbootloaderpartitions _)"
        
        if [[ "${DEVS}" == "" ]]; then
            DIALOG --msgbox $"No hard drives were found" 0 0
            return 1
        fi
        
        DIALOG --menu $"Select the boot device where the GRUB(2) bootloader will be installed (usually the MBR  and not a partition)." 14 55 7 ${DEVS} 2>${ANSWER} || return 1
        bootdev=$(cat ${ANSWER})
    fi
    
    if [[ "$(${_BLKID} -p -i -o value -s PTTYPE ${bootdev})" == "gpt" ]]; then
        CHECK_BIOS_BOOT_GRUB="1"
        CHECK_UEFISYS_PART=""
        RUN_CGDISK=""
        DISC="${bootdev}"
        check_gpt
    else
        if [[ "${FAIL_COMPLEX}" == "0" ]]; then
            DIALOG --defaultno --yesno $"Warning:\nSetup detected no GUID (gpt) partition table.\n\nGrub(2) has only space for approx. 30k core.img file. Depending on your setup, it might not fit into this gap and fail.\n\nDo you really want to install grub(2) to a msdos partition table?" 0 0 || return 1
        fi
    fi
    
    if [[ "${FAIL_COMPLEX}" == "1" ]]; then
        DIALOG --msgbox $"Error:\nGrub(2) cannot boot from ${bootdev}, which contains /boot!\n\nPossible error sources:\n- encrypted devices are not supported" 0 0
        return 1
    fi
    
    DIALOG --infobox $"Installing the GRUB(2) BIOS bootloader..." 0 0
    # freeze and unfreeze xfs filesystems to enable grub(2) installation on xfs filesystems
    freeze_xfs
    chroot_mount
    
    chroot "${DESTDIR}" "/usr/sbin/grub-install" \
        --directory="/usr/lib/grub/i386-pc" \
        --target="i386-pc" \
        --boot-directory="/boot" \
        --recheck \
        --debug \
        "${bootdev}" &>"/tmp/grub_bios_install.log"

    mkdir -p ${DESTDIR}/etc/grub.d
    cp -f /arch/10_linux ${DESTDIR}/etc/grub.d/

    sed -i 's/GRUB_TIMEOUT=5/GRUB_TIMEOUT=10/' ${DESTDIR}/etc/default/grub
    sed -i 's/GRUB_CMDLINE_LINUX_DEFAULT="quiet"/GRUB_CMDLINE_LINUX_DEFAULT=""/' ${DESTDIR}/etc/default/grub
    chroot "${DESTDIR}" grub-mkconfig -o /boot/grub/grub.cfg &>"/tmp/grub_config.log"
    
    chroot_umount
    
     
    if [[ -e "${DESTDIR}/boot/grub/i386-pc/core.img" ]]; then
        DIALOG --msgbox $"GRUB(2) BIOS has been successfully installed." 0 0
        
        GRUB_PREFIX_DIR="/boot/grub/"
        GRUB_BIOS="1"
        #dogrub_config



        GRUB_BIOS=""
    else
        DIALOG --msgbox $"Error installing GRUB(2) BIOS.\nCheck /tmp/grub_bios_install.log for more info.\n\nYou probably need to install it manually by chrooting into ${DESTDIR}.\nDon't forget to bind /dev and /proc into ${DESTDIR} before chrooting." 0 0
        return 1
    fi
    
}

dogrub_uefi_common() {
    
    dogrub_common_before
    
    DIALOG --msgbox $"Installing grub-efi-${UEFI_ARCH} now ..." 0 0
    PACKAGES="grub-common grub-efi-${UEFI_ARCH}"
    
    run_pacman
    # reset PACKAGES after installing
    PACKAGES=""
    
    chroot_mount
    
    chroot "${DESTDIR}" "/usr/sbin/grub-install" \
        --directory="/usr/lib/grub/${UEFI_ARCH}-efi" \
        --target="${UEFI_ARCH}-efi" \
        --efi-directory="/boot/efi" \
        --bootloader-id="arch_grub" \
        --boot-directory="/boot" \
        --recheck \
        --debug &>"/tmp/grub_uefi_${UEFI_ARCH}_install.log"
    

    chroot_umount
    
    mkdir -p "${DESTDIR}/boot/grub/locale"
    cp -f "${DESTDIR}/usr/share/locale/en@quot/LC_MESSAGES/grub.mo" "${DESTDIR}/boot/grub/locale/en.mo"
    
    
    BOOT_PART_FS_UUID="$(LD_LIBRARY_PATH="${DESTDIR}/usr/lib:${DESTDIR}/lib" "${DESTDIR}/usr/sbin/grub-probe" --target="fs_uuid" "${DESTDIR}/boot" 2>/dev/null)"
    BOOT_PART_FS="$(LD_LIBRARY_PATH="${DESTDIR}/usr/lib:${DESTDIR}/lib" "${DESTDIR}/usr/sbin/grub-probe" --target="fs" "${DESTDIR}/boot" 2>/dev/null)"
    
    BOOT_PART_HINTS_STRING="$(LD_LIBRARY_PATH="${DESTDIR}/usr/lib:${DESTDIR}/lib" "${DESTDIR}/usr/sbin/grub-probe" --target="hints_string" "${DESTDIR}/boot" 2>/dev/null)"
    
    [[ -e "${DESTDIR}/boot/grub/grub.cfg" ]] && mv "${DESTDIR}/boot/grub/grub.cfg" "${DESTDIR}/boot/grub/grub.cfg.save"
    
    cat << EOF > "${DESTDIR}/boot/grub/grub.cfg"

insmod usbms
insmod usb_keyboard

insmod part_gpt
insmod part_msdos

insmod fat
insmod iso9660
insmod udf
insmod ${BOOT_PART_FS}

insmod ext2
insmod reiserfs
insmod ntfs
insmod hfsplus

insmod linux
insmod chain

search --fs-uuid --no-floppy --set=root ${BOOT_PART_HINTS_STRING} ${BOOT_PART_FS_UUID}

if [ -f "(\${root})/grub/grub.cfg" ]; then
    set prefix="(\${root})/grub"
    source "(\${root})/grub/grub.cfg"
else
    if [ -f "(\${root})/boot/grub/grub.cfg" ]; then
        set prefix="(\${root})/boot/grub"
        source "(\${root})/boot/grub/grub.cfg"
    fi
fi

EOF
    
    cp -f "${DESTDIR}/boot/grub/grub.cfg" "${DESTDIR}/boot/efi/EFI/arch_grub/grub${SPEC_UEFI_ARCH}_standalone.cfg"
    
    __WD="${PWD}/"
    
    cd "${DESTDIR}/"
    
    chroot_mount
    
    chroot "${DESTDIR}" "/usr/bin/grub-mkstandalone" \
        --directory="/usr/lib/grub/${UEFI_ARCH}-efi" \
        --format="${UEFI_ARCH}-efi" \
        --compression="xz" \
        --output="/boot/efi/EFI/arch_grub/grub${SPEC_UEFI_ARCH}_standalone.efi" \
        "boot/grub/grub.cfg" &>"/tmp/grub_${UEFI_ARCH}_uefi_mkstandalone.log"
    
    chroot_umount
    
    cd "${__WD}/"
    
    [[ -e "${DESTDIR}/boot/grub/grub.cfg.save" ]] && mv "${DESTDIR}/boot/grub/grub.cfg.save" "${DESTDIR}/boot/grub/grub.cfg"
    
    cat "/tmp/grub_uefi_${UEFI_ARCH}_install.log" >> "${LOG}"
    
    if [[ -e "${DESTDIR}/boot/efi/EFI/arch_grub/grub${SPEC_UEFI_ARCH}.efi" ]] && [[ -e "${DESTDIR}/boot/grub/${UEFI_ARCH}-efi/core.efi" ]]; then
        _BOOTMGR_LABEL="Cinnarch (GRUB)"
        _BOOTMGR_LOADER_DIR="arch_grub"
        _BOOTMGR_LOADER_FILE="grub${SPEC_UEFI_ARCH}.efi"
        do_uefi_bootmgr_setup
        
        DIALOG --msgbox $"GRUB(2) UEFI ${UEFI_ARCH} has been successfully installed." 0 0
        
        GRUB_PREFIX_DIR="/boot/grub/"
        GRUB_UEFI="1"
        dogrub_config
        GRUB_UEFI=""
        
        DIALOG --defaultno --yesno $"Do you want to copy /boot/efi/EFI/arch_grub/grub${SPEC_UEFI_ARCH}.efi to /boot/efi/EFI/boot/boot${SPEC_UEFI_ARCH}.efi ?\n\nThis might be needed in some systems where efibootmgr may not work due to firmware issues." 0 0 && _UEFISYS_EFI_BOOT_DIR="1"
        
        if [[ "${_UEFISYS_EFI_BOOT_DIR}" == "1" ]]; then
            mkdir -p "${DESTDIR}/boot/efi/EFI/boot"
            
            rm -f "${DESTDIR}/boot/efi/EFI/boot/boot${SPEC_UEFI_ARCH}.efi"
            
            cp -f "${DESTDIR}/boot/efi/EFI/arch_grub/grub${SPEC_UEFI_ARCH}.efi" "${DESTDIR}/boot/efi/EFI/boot/boot${SPEC_UEFI_ARCH}.efi"
        fi
    else
        DIALOG --msgbox $"Error installing GRUB UEFI ${UEFI_ARCH}.\nCheck /tmp/grub_uefi_${UEFI_ARCH}_install.log for more info.\n\nYou probably need to install it manually by chrooting into ${DESTDIR}.\nDon't forget to bind /dev, /sys and /proc into ${DESTDIR} before chrooting." 0 0
        return 1
    fi
    
}

dogrub_uefi_x86_64() {
    
    do_uefi_x86_64
    
    dogrub_uefi_common
    
}

dogrub_uefi_i386() {
    
    do_uefi_i386
    
    dogrub_uefi_common
    
}


set_clock() {
    if [[ -e /usr/bin/tz ]]; then
        tz --setup && NEXTITEM="2"
    else
        DIALOG --msgbox $"Error:\ntz script not found, aborting clock setting" 0 0
    fi
}

set_language() {
    if [[ -e /usr/bin/lg ]]; then
        lg --setup && NEXTITEM="1"
    else
        DIALOG --msgbox $"Error:\nlg script not found, aborting language setting" 0 0
    fi
}


# run_mkinitcpio()
# runs mkinitcpio on the target system, displays output
#
run_mkinitcpio() {
    chroot_mount
    # all mkinitcpio output goes to /tmp/mkinitcpio.log, which we tail into a dialog
    ( \
    touch /tmp/setup-mkinitcpio-running
    echo "Initramfs progress ..." > /tmp/initramfs.log; echo >> /tmp/mkinitcpio.log
    chroot ${DESTDIR} /usr/bin/mkinitcpio -p ${KERNELPKG} >>/tmp/mkinitcpio.log 2>&1
    echo >> /tmp/mkinitcpio.log
    rm -f /tmp/setup-mkinitcpio-running
    ) &
    sleep 2
    dialog --backtitle "${TITLE}" --title $"Rebuilding initramfs images ..." --no-kill --tailboxbg "/tmp/mkinitcpio.log" 18 70
    while [[ -f /tmp/setup-mkinitcpio-running ]]; do
        /bin/true
    done
    chroot_umount
}

prepare_harddrive() {
    S_MKFSAUTO=0
    S_MKFS=0
    DONE=0
    NEXTITEM=""
    while [[ "${DONE}" = "0" ]]; do
        if [[ -n "${NEXTITEM}" ]]; then
            DEFAULT="--default-item ${NEXTITEM}"
        else
            DEFAULT=""
        fi
        CANCEL=""
        dialog ${DEFAULT} --backtitle "${TITLE}" --menu $"Prepare Hard Drive" 12 60 5 \
            "1" $"Auto-Prepare (erases the ENTIRE hard drive)" \
            "2" $"Partition Hard Drives (terminal)" \
            "3" $"Partitioning - Launch GParted (Graphical tool)" \
            "4" $"Create Software Raid, Lvm2 and Luks encryption" \
            "5" $"Set Filesystem Mountpoints" \
            "6" $"Return to Main Menu" 2>${ANSWER} || CANCEL="1"
        NEXTITEM="$(cat ${ANSWER})"
        [[ "${S_MKFSAUTO}" = "1" ]] && DONE=1
        case $(cat ${ANSWER}) in
            "1")
                autoprepare
                [[ "${S_MKFSAUTO}" = "1" ]] && DONE=1
                ;;
            "2")
                partition ;;
            "3")
                if [[ `which gparted` ]];then
                    /usr/sbin/gparted &>/dev/null &
                    DIALOG --msgbox $"Click 'OK' when you're done with GParted" 7 55

                else
                    DIALOG --msgbox $"Gparted is not available in Cinnarch minimum \n\nDownload the regular Cinnarch version to use it." 9 55
                fi
                NEXTITEM="5" ;;
            "4")
                create_special ;;
            "5")
                PARTFINISH=""
                ASK_MOUNTPOINTS="1"
                mountpoints ;;
            *)
                DONE=1 ;;
        esac
    done
    if [[ "${CANCEL}" = "1" ]]; then
        NEXTITEM="2"
    else
        NEXTITEM="3"
    fi
}

# menu for raid, lvm and encrypt
create_special() {
    NEXTITEM=""
    SPECIALDONE=0
    while [[ "${SPECIALDONE}" = "0" ]]; do
        if [[ -n "${NEXTITEM}" ]]; then
            DEFAULT="--default-item ${NEXTITEM}"
        else
            DEFAULT=""
        fi
        CANCEL=""
        dialog ${DEFAULT} --backtitle "${TITLE}" --menu $"Create Software Raid, LVM2 and Luks encryption" 14 60 5 \
            "1" $"Create Software Raid" \
            "2" $"Create LVM2" \
            "3" $"Create Luks encryption" \
            "4" $"Return to Previous Menu" 2>${ANSWER} || CANCEL="1"
        NEXTITEM="$(cat ${ANSWER})"
        case $(cat ${ANSWER}) in
            "1")
                _createmd ;;
            "2")
                _createlvm ;;
            "3")
                _createluks ;;
            *)
                SPECIALDONE=1 ;;
        esac
    done
    if [[ "${CANCEL}" = "1" ]]; then
        NEXTITEM="4"
    else
        NEXTITEM="5"
    fi
}

# menu for md creation
_createmd() {
    NEXTITEM=""
    MDDONE=0
    while [[ "${MDDONE}" = "0" ]]; do
        if [[ -n "${NEXTITEM}" ]]; then
            DEFAULT="--default-item ${NEXTITEM}"
        else
            DEFAULT=""
        fi
        CANCEL=""
        dialog ${DEFAULT} --backtitle "${TITLE}" --menu $"Create Software Raid" 12 60 5 \
            "1" $"Raid Help" \
            "2" $"Reset Software Raid completely" \
            "3" $"Create Software Raid" \
            "4" $"Create Partitionable Software Raid" \
            "5" $"Return to Previous Menu" 2>${ANSWER} || CANCEL="1"
        NEXTITEM="$(cat ${ANSWER})"
        case $(cat ${ANSWER}) in
            "1")
                _helpraid ;;
            "2")
                _stopmd ;;
            "3")
                RAID_PARTITION=""
                _raid ;;
            "4")
                RAID_PARTITION="1"
                _raid ;;
              *)
                MDDONE=1 ;;
        esac
    done
    if [[ "${CANCEL}" = "1" ]]; then
        NEXTITEM="1"
    else
        NEXTITEM="4"
    fi
}

# menu for lvm creation
_createlvm() {
    NEXTITEM=""
    LVMDONE=0
    while [[ "${LVMDONE}" = "0" ]]; do
        if [[ -n "${NEXTITEM}" ]]; then
            DEFAULT="--default-item ${NEXTITEM}"
        else
            DEFAULT=""
        fi
        CANCEL=""
        dialog ${DEFAULT} --backtitle "${TITLE}" --menu $"Create physical volume, volume group or logical volume" 13 60 7 \
            "1" $"LVM Help" \
            "2" $"Reset Logical Volume completely" \
            "3" $"Create Physical Volume" \
            "4" $"Create Volume Group" \
            "5" $"Create Logical Volume" \
            "6" $"Return to Previous Menu" 2>${ANSWER} || CANCEL="1"
        NEXTITEM="$(cat ${ANSWER})"
        case $(cat ${ANSWER}) in
            "1")
                _helplvm ;;
            "2")
                _stoplvm ;;
            "3")
                _createpv ;;
            "4")
                _createvg ;;
            "5")
                _createlv ;;
              *)
                LVMDONE=1 ;;
        esac
    done
    if [[ "${CANCEL}" = "1" ]]; then
        NEXTITEM="2"
    else
        NEXTITEM="4"
    fi
}

# menu for luks creation
_createluks() {
    NEXTITEM=""
    LUKSDONE=0
    while [[ "${LUKSDONE}" = "0" ]]; do
        if [[ -n "${NEXTITEM}" ]]; then
            DEFAULT="--default-item ${NEXTITEM}"
        else
            DEFAULT=""
        fi
        CANCEL=""
        dialog ${DEFAULT} --backtitle "${TITLE}" --menu $"Create Luks Encryption" 12 60 5 \
            "1" $"Luks Help" \
            "2" $"Reset Luks Encryption completely" \
            "3" $"Create Luks" \
            "4" $"Return to Previous Menu" 2>${ANSWER} || CANCEL="1"
        NEXTITEM="$(cat ${ANSWER})"
        case $(cat ${ANSWER}) in
            "1")
                _helpluks ;;
            "2")
                _stopluks ;;
            "3")
                _luks ;;
              *)
                LUKSDONE=1 ;;
        esac
    done
    if [[ "${CANCEL}" = "1" ]]; then
        NEXTITEM="3"
    else
        NEXTITEM="4"
    fi
}

auto_hwdetect() {
    HWDETECT=""
    FBPARAMETER=""
    HWPARAMETER=""
    HWDETECTMODULES=""
    HWDETECTHOOKS=""
    HWDETECTFILES=""
    HWKVER==
    DIALOG --yesno $"PRECONFIGURATION?\n-----------------\n\nDo you want to use 'hwdetect' for:\n'/etc/mkinitcpio.conf'?\n\nThis ensures consistent ordering of your hard disk / usb controllers, network and sound devices.\n\nIt is recommended to say 'YES' here." 18 70 && HWDETECT="yes"
    if [[ "${HWDETECT}" = "yes" ]]; then
        # check on usb input
        [[ "$(lsmod | grep ^hid)" ]] && HWPARAMETER="${HWPARAMETER} --usbinput"
        # check on framebuffer modules and kms
        if [[ -e ${DESTDIR}/lib/initcpio/hooks/v86d && "$(grep -w uvesafb /proc/cmdline)" ]]; then
             FBPARAMETER="--uvesafb"
             HWDETECTFILES="/etc/modprobe.d/uvesafb.conf"
        fi
        # [[ "$(grep "radeon" /etc/modprobe.d/modprobe.conf)" ]] && (FBPARAMETER="--ati-kms";HWDETECTFILES="/etc/modprobe.d/modprobe.conf")
        # [[ "$(grep "i915" /etc/modprobe.d/modprobe.conf)" ]] && (FBPARAMETER="--intel-kms";HWDETECTFILES="/etc/modprobe.d/modprobe.conf")
        # [[ "$(grep "nouveau" /etc/modprobe.d/modprobe.conf)" ]] && (FBPARAMETER="--nvidia-kms";HWDETECTFILES="/etc/modprobe.d/modprobe.conf")
        # [[ "$(grep -w fbmodule /proc/cmdline)" ]] && FBPARAMETER="--fbmodule"
        
        if [[ "$(lsmod | grep ^pcmcia)" ]]; then
            DIALOG --defaultno --yesno $"Setup detected pcmcia hardware...\nDo you need support for booting from pcmcia devices?" 0 0 && HWPARAMETER="${HWPARAMETER} --pcmcia"
        fi
        if [[ "$(lsmod | grep ^nfs)" ]]; then
            DIALOG --defaultno --yesno $"Setup detected nfs driver...\nDo you need support for booting from nfs shares?" 0 0 && HWPARAMETER="${HWPARAMETER} --nfs"
        fi
        if [[ -e ${DESTDIR}/lib/initcpio/hooks/dmraid ]]; then
            if ! [[ "$(dmraid -r | grep ^no )" ]]; then
                HWPARAMETER="${HWPARAMETER} --dmraid"
            fi
        fi
        if [[ -e "/tmp/card_nvidia" ]];then
            sed -i 's/^MODULES=(/MODULES=(nouveau /' ${DESTDIR}/etc/mkinitcpio.conf
        fi
        if [[ -e "/tmp/card_ati" ]];then
            sed -i 's/^MODULES=(/MODULES=(radeon /' ${DESTDIR}/etc/mkinitcpio.conf
        fi
        if [[ -e "/tmp/card_intel" ]];then
            sed -i 's/^MODULES=(/MODULES=(i915 /' ${DESTDIR}/etc/mkinitcpio.conf
        fi
        # check for separate /usr partition
        [[ $(mount | grep "${DESTDIR}/usr ") ]] && HWPARAMETER="${HWPARAMETER} --shutdown"
        [[ "$(${_BLKID} -p -i -o value -s TYPE ${PART_ROOT})" = "btrfs" ]] && HWPARAMETER="${HWPARAMETER} --btrfs"
        offset=$(hexdump -s 526 -n 2 -e '"%0d"' "${DESTDIR}/boot/${VMLINUZ}")
        read HWKER _ < <(dd if="${DESTDIR}/boot/${VMLINUZ}" bs=1 count=127 skip=$(( offset + 0x200 )) 2>/dev/null)
        HWDETECTMODULES="$(echo $(hwdetect --kernel_directory=${DESTDIR} --kernel_version=${HWKVER} ${FBPARAMETER} --hostcontroller --filesystem ${HWPARAMETER}) | sed -e 's#.*\" ##g')"
        HWDETECTHOOKS="$(hwdetect --kernel_directory=${DESTDIR} --kernel_version=${HWKVER} --rootdevice=${PART_ROOT} --hooks-dir=${DESTDIR}/usr/lib/initcpio/install ${FBPARAMETER} ${HWPARAMETER} --hooks)"
        [[ -n "${HWDETECTMODULES}" ]] && sed -i -e "s/^MODULES=.*/${HWDETECTMODULES}/g" ${DESTDIR}/etc/mkinitcpio.conf
        [[ -n "${HWDETECTHOOKS}" ]] && sed -i -e "s/^HOOKS=.*/${HWDETECTHOOKS}/g" ${DESTDIR}/etc/mkinitcpio.conf
        [[ -n "${HWDETECTFILES}" ]] && sed -i -e "s#^FILES=.*#FILES=\"${HWDETECTFILES}\"#g" ${DESTDIR}/etc/mkinitcpio.conf  


    fi
}

auto_fb() {
    UVESAFB=""
    # clean modprobe.conf file from options first
    # sed -i -e '/options/d' ${DESTDIR}/etc/modprobe.d/modprobe.conf
    # grep ^[a-z] /etc/modprobe.d/modprobe.conf >> ${DESTDIR}/etc/modprobe.d/modprobe.conf
    if [[ -e ${DESTDIR}/lib/initcpio/hooks/v86d && "$(grep -w uvesafb /proc/cmdline)" ]]; then
        UVESAFB="$(grep ^[a-z] /etc/modprobe.d/uvesafb.conf)" 
        sed -i -e "s#options.*#${UVESAFB}#g" ${DESTDIR}/etc/modprobe.d/uvesafb.conf
    fi
}

auto_parameters() {

       
    _do_locales


    if [[ -s  /tmp/.timezone ]]; then
        DIALOG --infobox $"Setting the timezone: $(cat /tmp/.timezone | sed -e 's/\..*//g') ..." 0 0
        chroot ${DESTDIR} ln -s /usr/share/zoneinfo/$(cat /tmp/.timezone | sed -e 's/\..*//g') /etc/localtime
            
    fi

}

auto_luks() {
    # remove root device from crypttab
    if [[ -e /tmp/.crypttab && "$(grep -v '^#' ${DESTDIR}/etc/crypttab)"  = "" ]]; then
        # add to temp crypttab
        sed -i -e "/^$(basename ${PART_ROOT}) /d" /tmp/.crypttab
        cat /tmp/.crypttab >> ${DESTDIR}/etc/crypttab
    fi
}

auto_timesetting() {
    hwclock --systohc --utc
    cp /etc/adjtime ${DESTDIR}/etc/adjtime
}

auto_ftpmirror() {
    # /etc/pacman.d/mirrorlist
    # add installer-selected mirror to the top of the mirrorlist
    while [[ -f '/tmp/.rankmirrors' ]]; do
        /bin/true
    done;
    mv /tmp/.mirrorlist "${DESTDIR}/etc/pacman.d/mirrorlist"
}

_set_50-synaptics() {
    cat << EOF > ${DESTDIR}/etc/X11/xorg.conf.d/50-synaptics.conf 
# Example xorg.conf.d snippet that assigns the touchpad driver
# to all touchpads. See xorg.conf.d(5) for more information on
# InputClass.
# DO NOT EDIT THIS FILE, your distribution will likely overwrite
# it when updating. Copy (and rename) this file into
# /etc/X11/xorg.conf.d first.
# Additional options may be added in the form of
#   Option "OptionName" "value"
#
Section "InputClass"
        Identifier "touchpad catchall"
        Driver "synaptics"
        MatchIsTouchpad "on"
        Option "TapButton1" "1"
        Option "TapButton2" "2"
        Option "TapButton3" "3"
# This option is recommend on all Linux systems using evdev, but cannot be
# enabled by default. See the following link for details:
# http://who-t.blogspot.com/2010/11/how-to-ignore-configuration-errors.html
        MatchDevicePath "/dev/input/event*"
EndSection

Section "InputClass"
        Identifier "touchpad ignore duplicates"
        MatchIsTouchpad "on"
        MatchOS "Linux"
        MatchDevicePath "/dev/input/mouse*"
        Option "Ignore" "on"
EndSection

# This option enables the bottom right corner to be a right button on
# non-synaptics clickpads.
# This option is only interpreted by clickpads.
Section "InputClass"
        Identifier "Default clickpad buttons"
        MatchDriver "synaptics"
        Option "SoftButtonAreas" "50% 0 82% 0 0 0 0 0"
EndSection

# This option disables software buttons on Apple touchpads.
# This option is only interpreted by clickpads.
Section "InputClass"
        Identifier "Disable clickpad buttons on Apple touchpads"
        MatchProduct "Apple|bcm5974"
        MatchDriver "synaptics"
        Option "SoftButtonAreas" "0 0 0 0 0 0 0 0"
EndSection
EOF

}


configure_system() {
    destdir_mounts || return 1
    ## PREPROCESSING ##
    # only done on first invocation of configure_system and redone on canceled configure system
    if [[ ${S_CONFIG} -eq 0 ]]; then

        mkdir -p ${DESTDIR}/usr/share/cinnarch/
        cp /usr/share/cinnarch/cinnarch_menu.png ${DESTDIR}/usr/share/cinnarch/cinnarch_menu.png

        auto_ftpmirror
        auto_parameters
        auto_fb
        auto_hwdetect
    fi
    ## END PREPROCESS ##
    geteditor || return 1
    FILE=""
    CONTROL_HOSTNAME=0
    CONTROL_USER=0


    ## populate keyring
    cp -f /usr/bin/pacman-key ${DESTDIR}/usr/bin/pacman-key

    cp -f /usr/lib/systemd/system/lightdm.service ${DESTDIR}/usr/lib/systemd/system/lightdm.service
    cp -f /etc/systemd/system/pacman-init.service ${DESTDIR}/usr/lib/systemd/system/pacman-init.service
    chroot ${DESTDIR} systemctl enable lightdm.service NetworkManager.service pacman-init.service >/dev/null 2>&1
    if [[ -f /tmp/use_ntp ]];then
        chroot ${DESTDIR} systemctl enable ntpd.service >/dev/null 2>&1
    fi


    cp -f /etc/pacman.conf ${DESTDIR}/etc/pacman.conf
    cp -f /etc/yaourtrc ${DESTDIR}/etc/yaourtrc



    

    while true; do
        S_CONFIG=0

        if [[ -n "${FILE}" ]]; then
            DEFAULT="--default-item ${FILE}"
        else
            DEFAULT=""
        fi
        
        DIALOG ${DEFAULT} --menu $"Configuration" 20 80 15 \
                "Desktop-User"                  $"Create your user" \
                "Hostname"                      $"Your computer's name" \
                "Root-Password"                 $"Set the root password" \
                "/etc/mkinitcpio.conf"          $"(Optional) Initramfs Config" \
                "Return"                        $"Return to Main Menu" 2>${ANSWER} || break
    
        
        FILE="$(cat ${ANSWER})"
        if [[ "${FILE}" = "Return" || -z "${FILE}" ]]; then       # exit
            S_CONFIG=1
            break

        elif [[ "${FILE}" = "Desktop-User" ]]; then
            USER_NAME_TMP=""
            USER_NAME=""
            USER_PASSWORD=""
            USER_FULL_NAME=""

            if [[ "${CONTROL_USER}" = 0 ]]; then

                while [[ "${USER_NAME_TMP}" = "" ]]; do
                    DIALOG --inputbox $"Enter your user name (no spaces):" 9 40 2>${ANSWER} || return 1
                    USER_NAME_TMP=$(cat ${ANSWER})
                    USER_NAME=${USER_NAME_TMP,,}
                    rm -f ${DESTDIR}/etc/sudoers
                    echo "root ALL=(ALL) ALL" > ${DESTDIR}/etc/sudoers
                    echo "${USER_NAME} ALL=(ALL) ALL" >> ${DESTDIR}/etc/sudoers
                    #cp -f /arch/sudoers ${DESTDIR}/etc/sudoers
                    #sed -i "s|^cinnarch|${USER_NAME}|g" ${DESTDIR}/etc/sudoers
                    chmod 440 ${DESTDIR}/etc/sudoers

                    DIALOG --inputbox $"Enter your full name:" 9 40 2>${ANSWER} || return 1
                    USER_FULL_NAME=$(cat ${ANSWER})
                    
                done

                while [[ "${USER_PASSWORD}" = "" ]]; do
                        DIALOG --insecure --passwordbox $"Enter your user password:" 0 0 2>${ANSWER} || return 1
                        PASS=$(cat ${ANSWER})
                        DIALOG --insecure --passwordbox $"Retype your user password:" 0 0 2>${ANSWER} || return 1
                        PASS2=$(cat ${ANSWER})
                        if [[ "${PASS}" = "${PASS2}" ]]; then
                            USER_PASSWORD=${PASS}
                            echo ${USER_PASSWORD} > /tmp/.user_password
                            echo ${USER_PASSWORD} >> /tmp/.user_password
                            USER_PASSWORD=/tmp/.user_password
                        else
                         DIALOG --msgbox $"Password didn't match, please enter again." 0 0
                        fi
                done

                DIALOG --infobox $"Creating user..." 4 30

                cp -rf /etc/skel ${DESTDIR}/etc/  >/dev/null 2>&1
                rm -rf ${DESTDIR}/etc/skel/Desktop >/dev/null 2>&1
                chroot ${DESTDIR} useradd -m -s /bin/bash -g users -G lp,video,network,storage,wheel,audio ${USER_NAME} >/dev/null 2>&1
                chroot ${DESTDIR} passwd ${USER_NAME} < /tmp/.user_password >/dev/null 2>&1
                chroot ${DESTDIR} chfn -f "${USER_FULL_NAME}" "${USER_NAME}" >/dev/null 2>&1
                
                rm /tmp/.user_password


                cp -rf /etc/skel/.config /etc/skel/.gconf /etc/skel/.cache /etc/skel/.local /etc/skel/.gnome2 /etc/skel/.gtkrc-2 ${DESTDIR}/home/${USER_NAME}/ >/dev/null 2>&1
                chroot ${DESTDIR} chown -R ${USER_NAME}:users /home/${USER_NAME} >/dev/null 2>&1


                CONTROL_USER=1
            else
                DIALOG --msgbox $"User has already been created" 6 35
            fi

        elif [[ "${FILE}" = "Hostname" ]]; then
            HOSTNAME=""

            if [[ "${CONTROL_HOSTNAME}" = 0 ]];then

                while [[ "${HOSTNAME}" = "" ]]; do
                    DIALOG --inputbox $"Enter your computer's name:" 0 0 2>${ANSWER} || return 1
                    HOSTNAME=$(cat ${ANSWER})
                    if [[ ! -f ${DESTDIR}/etc/hostname ]]; then
                        echo ${HOSTNAME} > ${DESTDIR}/etc/hostname
                    fi
                done 
                CONTROL_HOSTNAME=1
            else       
                DIALOG --msgbox $"Hostname has already been set up" 6 40
            fi


        elif [[ "${FILE}" = "/etc/mkinitcpio.conf" ]]; then    # non-file
            
            DIALOG --msgbox $"The mkinitcpio.conf file controls which modules will be placed into the initramfs for your system's kernel.\n\n- Non US keymap users should add 'keymap' to HOOKS= array\n- USB keyboard users should add 'usbinput' to HOOKS= array\n- If you install under VMWARE add 'BusLogic' to MODULES= array\n- raid, lvm2, encrypt are not enabled by default\n- 2 or more disk controllers, please specify the correct module\n  loading order in MODULES= array \n\nMost of you will not need to change anything in this file." 18 70
            HOOK_ERROR=""
            ${EDITOR} ${DESTDIR}${FILE}
            for i in $(cat ${DESTDIR}/etc/mkinitcpio.conf | grep ^HOOKS | sed -e 's/"//g' -e 's/HOOKS=//g'); do
                [[ -e ${DESTDIR}/usr/lib/initcpio/install/${i} ]] || HOOK_ERROR=1
            done
            if [[ "${HOOK_ERROR}" = "1" ]]; then
                DIALOG --msgbox $"ERROR: Detected error in 'HOOKS=' line, please correct HOOKS= in /etc/mkinitcpio.conf!" 18 70
            fi


        elif [[ "${FILE}" = "Root-Password" ]]; then            # non-file
            PASSWORD=""
            while [[ "${PASSWORD}" = "" ]]; do
                DIALOG --insecure --passwordbox $"Enter root password:" 0 0 2>${ANSWER} || return 1
                PASS=$(cat ${ANSWER})
                DIALOG --insecure --passwordbox $"Retype root password:" 0 0 2>${ANSWER} || return 1
                PASS2=$(cat ${ANSWER})
                if [[ "${PASS}" = "${PASS2}" ]]; then
                    PASSWORD=${PASS}
                    echo ${PASSWORD} > /tmp/.password
                    echo ${PASSWORD} >> /tmp/.password
                    PASSWORD=/tmp/.password
                else
                    DIALOG --msgbox $"Password didn't match, please enter again." 0 0
                fi
            done
            chroot ${DESTDIR} passwd root < /tmp/.password
            rm /tmp/.password
        else                                                #regular file
            ${EDITOR} ${DESTDIR}${FILE}
        fi
    done
    if [[ ${S_CONFIG} -eq 1 ]]; then

        ###### USER CONFIGURATIONS  #####

        ## Set defaults directories
        chroot ${DESTDIR} su -c "xdg-user-dirs-update" ${USER_NAME} || true

        ## Unmute alsa channels
        chroot ${DESTDIR} amixer -c 0 set Master playback 100% unmute>/dev/null 2>&1


        ## Copy locales
        cp -f /tmp/locale.gen ${DESTDIR}/etc/locale.gen

        # only done on normal exit of configure menu
        ## POSTPROCESSING ##
        # adjust time
        auto_timesetting

        # /etc/initcpio.conf
        # Fix deprecated hooks
        sed -i 's/ pata//' ${DESTDIR}/etc/mkinitcpio.conf
        sed -i 's/ scsi//' ${DESTDIR}/etc/mkinitcpio.conf
        sed -i 's/ sata//' ${DESTDIR}/etc/mkinitcpio.conf
        sed -i 's/ filesystem/ block filesystem/' ${DESTDIR}/etc/mkinitcpio.conf
        run_mkinitcpio
        
        # /etc/locale.gen
        sleep 2
        DIALOG --infobox $"Generating locales..." 4 25
        cp -f /tmp/locale.conf ${DESTDIR}/etc/locale.conf
        chroot ${DESTDIR} locale-gen >/dev/null 2>&1


        # Set gsettings
        cp /arch/set-gsettings ${DESTDIR}/usr/bin/set-gsettings
        mkdir -p ${DESTDIR}/var/run/dbus
        mount -o bind /var/run/dbus ${DESTDIR}/var/run/dbus
        chroot ${DESTDIR} su -c "/usr/bin/set-gsettings" ${USER_NAME} >/dev/null 2>&1
        rm ${DESTDIR}/usr/bin/set-gsettings

        # Fix transmission leftover
        mv ${DESTDIR}/usr/lib/tmpfiles.d/transmission.conf ${DESTDIR}/usr/lib/tmpfiles.d/transmission.conf.backup

        # Configure touchpad
        _set_50-synaptics
        # cp /etc/X11/xorg.conf.d/10-synaptics.conf ${DESTDIR}/etc/X11/xorg.conf.d/10-synaptics.conf

        # Fix grub locale error
        chroot ${DESTDIR} cp "/boot/grub/locale/en@quot.mo" "/boot/grub/locale/$(echo ${LOCALE}|cut -b 1-2).mo.gz"

        # Fix QT apps
        echo 'export GTK2_RC_FILES="$HOME/.gtkrc-2.0"' >> ${DESTDIR}/etc/bash.bashrc

        # Change pantheon-greeter wallpaper
        chroot ${DESTDIR} unlink /usr/share/backgrounds/cinnarch-default
        chroot ${DESTDIR} ln -s /usr/share/cinnarch/wallpapers/83II_by_bo0xVn.jpg /usr/share/backgrounds/cinnarch-default

        # Set Cinnarch name in filesystem files
        cp /etc/arch-release ${DESTDIR}/etc
        cp /etc/issue ${DESTDIR}/etc
        cp -f /etc/os-release ${DESTDIR}/etc/os-release

        # Set Adwaita cursor theme
        chroot ${DESTDIR} ln -s /usr/share/icons/Adwaita /usr/share/icons/default

        # Fix multilib repo in last release
        cp -f /etc/pacman.conf ${DESTDIR}/etc/pacman.conf

        if [[ $(uname -m) = 'x86_64' ]];then
            echo "" >> ${DESTDIR}/etc/pacman.conf
            echo "[multilib]" >> ${DESTDIR}/etc/pacman.conf
            echo "SigLevel = PackageRequired" >> ${DESTDIR}/etc/pacman.conf
            echo "Include = /etc/pacman.d/mirrorlist" >> ${DESTDIR}/etc/pacman.conf
        fi


        ## END POSTPROCESSING ##
    fi
}

install_bootloader_uefi_x86_64() {
    
    DIALOG --menu $"Which x86_64 UEFI bootloader would you like to use?" 13 55 2 \
        "EFISTUB_x86_64" $"Only x86_64 Kernels" \
        "GRUB_UEFI_x86_64" $"GRUB(2) x86_64 UEFI" 2>${ANSWER} || CANCEL=1
    case $(cat ${ANSWER}) in
        "EFISTUB_x86_64") do_efistub_uefi_x86_64 ;;
        "GRUB_UEFI_x86_64") dogrub_uefi_x86_64 ;;
    esac
    
}

install_bootloader_uefi_i386() {
    
    DIALOG --menu $"Which i386 UEFI bootloader would you like to use?" 13 55 2 \
        "EFISTUB_i686" $"Only i686 Kernels" \
        "GRUB_UEFI_i386" $"GRUB(2) i386 UEFI" 2>${ANSWER} || CANCEL=1
    case $(cat ${ANSWER}) in
        "EFISTUB_i686") do_efistub_uefi_i686 ;;
        "GRUB_UEFI_i386") dogrub_uefi_i386 ;;
    esac
    
}


install_bootloader() {
    
    destdir_mounts || return 1
    if [[ "${NAME_SCHEME_PARAMETER_RUN}" == "" ]]; then
        set_device_name_scheme || return 1
    fi
    pacman_conf
    prepare_pacman
    CANCEL=""
    
    _DIRECT="0"
    
    [[ "$(grep UEFI_ARCH_x86_64 /proc/cmdline)" ]] && _UEFI_x86_64="1"
    
    [[ "${_UEFI_x86_64}" == "1" ]] && DIALOG --yesno $"Setup has detected that you are using x86_64 (64-bit) UEFI ...\nDo you like to install a x86_64 UEFI bootloader?" 0 0 && install_bootloader_uefi_x86_64 && _DIRECT="1"
    
    if [[ "${_DIRECT}" == "1" ]]; then
        DIALOG --yesno $"Do you want to install another bootloader?" 0 0 && install_bootloader_menu && _DIRECT="0"
    else
        install_bootloader_menu
    fi
}

install_bootloader_menu() {
    
    DIALOG --menu $"What is your boot system type?" 10 40 3 \
        "GRUB2" $"BIOS (Common)" \
        "UEFI_x86_64" $"x86_64 UEFI" \
        "UEFI_i386" $"i386 UEFI" 2>${ANSWER} || CANCEL=1
    case $(cat ${ANSWER}) in
        "GRUB2") dogrub_bios ;;
        "UEFI_x86_64") install_bootloader_uefi_x86_64 ;;
        "UEFI_i386") install_bootloader_uefi_i386 ;;
    esac
    
    if [[ "${CANCEL}" = "1" ]]; then
        NEXTITEM="4"
    else
        NEXTITEM="4"
    fi
}

mainmenu() {
    if [[ -n "${NEXTITEM}" ]]; then
        DEFAULT="--default-item ${NEXTITEM}"
    else
        DEFAULT=""
    fi
    dialog ${DEFAULT} --backtitle "${TITLE}" --title $" MAIN MENU " \
    --menu $"Use the UP and DOWN arrows to navigate menus.\nUse TAB to switch between buttons and ENTER to select." 17 58 13 \
    "0" $"Set Language" \
    "1" $"Set Time And Date" \
    "2" $"Prepare Hard Drive" \
    "3" $"Install System" \
    "4" $"Configure System" \
    "5" $"Exit Install" 2>${ANSWER}
    NEXTITEM="$(cat ${ANSWER})"


    case $(cat ${ANSWER}) in
        "0")
            set_language ;;
        "1")
            set_clock ;;
        "2")
            prepare_harddrive ;;

        "3")
            select_packages
            install_bootloader ;;
        "4")
            configure_system
             
            DIALOG --yesno $"The installation is complete. \nDo you want to restart to your new system?" 0 0 && RESTART_CHECK='S'
            if [[ "${RESTART_CHECK}" == 'S' ]];then
                reboot
            fi
            ;;
        "5")
            

            if [[ "${S_SRC}" = "1" && "${MODE}" = "media" ]]; then
                umount "${_MEDIA}" >/dev/null 2>&1
            fi
            [[ -e /tmp/.setup-running ]] && rm /tmp/.setup-running
            clear
            echo ""
            echo "If the install finished successfully, you can now type 'reboot'"
            echo "to restart the system."
            echo ""
            exit 0 ;;
        *)
            DIALOG --yesno $"Abort Installation?" 6 40 && [[ -e /tmp/.setup-running ]] && rm /tmp/.setup-running && clear && exit 0
            
            ;;

    esac

}

#####################
## begin execution ##
if [[ -e /tmp/.setup-running ]]; then
    DIALOG --yesno $"Wait! \n\nCinnarch Installer is already running somewhere else! \n\nDo you want to start from the beginning?" 0 0 && rm /tmp/.setup-running /tmp/.km-running /tmp/setup-pacman-running /tmp/setup-mkinitcpio-running /tmp/.tz-running /tmp/.setup
    if [[ -e /tmp/.setup-running ]]; then
        exit 1
    fi
fi

while [[ "$NETWORK_ALIVE" != "" ]];do
    DIALOG --msgbox $"You have to configure your Internet connection before proceed. \n\nThen press 'OK'" 8 50
    NETWORK_ALIVE=`ping -c1 google.com 2>&1 | grep unknown`
done

if [[ "$NETWORK_ALIVE" = "" ]];then

    : >/tmp/.setup-running
    : >/tmp/.setup




    DIALOG --infobox $"Checking for Cinnarch Installer Updates..." 6 50
    INSTALLER_VERSION_NET=`curl http://www.cinnarch.com/cinnarch_installer/version 2>/dev/null`

    if [[ ${INSTALLER_VERSION} < ${INSTALLER_VERSION_NET} ]];then
            if [[ ${INSTALLER_VERSION} < 0.5 ]];then
                DIALOG --msgbox $"Your version is too old. \n\nPlease, download the last Cinnarch Live" 7 50
            else

                ${DLPROG} -O /arch/setup http://www.cinnarch.com/cinnarch_installer/setup 2>/dev/null
            
                DIALOG --msgbox $"Successfully updated. \n\nPlease, restart Cinnarch Installer" 7 50

            fi

            rm /tmp/.setup-running
            exit 1
    fi



    DIALOG --msgbox $"Welcome to the Cinnarch Installation program.\n\nThe install process is fairly straightforward, and you should run through the options in the order they are presented.\n\nIf you are unfamiliar with partitioning/making filesystems, you may want to consult some documentation before continuing.\n\nYou have Gparted as a visual app for the partition task available with Cinnarch" 18 65
    sh /arch/rankmirrors-script &

    while true; do
        mainmenu
    done

fi


clear
exit 0

# vim: set ts=4 sw=4 et:

'''
