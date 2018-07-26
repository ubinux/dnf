#!/bin/bash

HIDDENROOTFS=$1
REPODIR=$2
SPDXREPODIR=$3
SPDXDIR=$4
SRPMREPODIR=$5
SRPMDIR=$6
RPMREPODIR=$7
RPMDIR=$8
TARGETROOTFS=$9
WORKDIR=`pwd`

Export_env () {
    echo "export TARGET_ROOTFS=$TARGETROOTFS" > $WORKDIR/.env-dnf
    echo "export HIDDEN_ROOTFS=$HIDDENROOTFS" >> $WORKDIR/.env-dnf
    echo "export REPO_DIR=$REPODIR" >> $WORKDIR/.env-dnf
    echo "export SPDX_REPO_DIR=$SPDXREPODIR" >> $WORKDIR/.env-dnf
    echo "export SPDX_DESTINATION_DIR=$SPDXDIR" >> $WORKDIR/.env-dnf
    echo "export SRPM_REPO_DIR=$SRPMREPODIR" >> $WORKDIR/.env-dnf
    echo "export SRPM_DESTINATION_DIR=$SRPMDIR" >> $WORKDIR/.env-dnf
    echo "export RPM_REPO_DIR=$RPMREPODIR" >> $WORKDIR/.env-dnf
    echo "export RPM_DESTINATION_DIR=$RPMDIR" >> $WORKDIR/.env-dnf
    echo "export LD_LIBRARY_PATH=$OECORE_NATIVE_SYSROOT/usr/bin/../lib/pseudo/lib:$OECORE_NATIVE_SYSROOT/usr/bin/../lib/pseudo/lib64" >> $WORKDIR/.env-dnf
    echo "export LD_PRELOAD=libpseudo.so" >> $WORKDIR/.env-dnf
    echo "export PSEUDO_PASSWD=$HIDDENROOTFS" >> $WORKDIR/.env-dnf 
    echo "export PSEUDO_OPTS=" >> $WORKDIR/.env-dnf
    echo "export PSEUDO_LIBDIR=$OECORE_NATIVE_SYSROOT/usr/bin/../lib/pseudo/lib64" >> $WORKDIR/.env-dnf
    echo "export PSEUDO_NOSYMLINKEXP=1" >> $WORKDIR/.env-dnf
    echo "export PSEUDO_DISABLED=0" >> $WORKDIR/.env-dnf
    echo "export PSEUDO_PREFIX=$OECORE_NATIVE_SYSROOT/usr" >> $WORKDIR/.env-dnf
    echo "export PSEUDO_LOCALSTATEDIR=$WORKDIR/pseudo/" >> $WORKDIR/.env-dnf
    echo "export D=$HIDDENROOTFS" >> $WORKDIR/.env-dnf
    echo "export OFFLINE_ROOT=$HIDDENROOTFS" >> $WORKDIR/.env-dnf
    echo "export IPKG_OFFLINE_ROOT=$HIDDENROOTFS" >> $WORKDIR/.env-dnf
    echo "export OPKG_OFFLINE_ROOT=$HIDDENROOTFS" >> $WORKDIR/.env-dnf
    echo "export INTERCEPT_DIR=$WORKDIR/intercept_scripts" >> $WORKDIR/.env-dnf
    echo "export NATIVE_ROOT=$OECORE_NATIVE_SYSROOT" >> $WORKDIR/.env-dnf
    echo "export RPM_ETCCONFIGDIR=$HIDDENROOTFS" >> $WORKDIR/.env-dnf
}

Check_para () {
#Check the parameters
if [ -z "${REPO_DIR}" -o ${HIDDEN_ROOTFS} = "--help" -o ${HIDDEN_ROOTFS} = "-h" -o ${HIDDEN_ROOTFS} = "-H" ]; then
    echo ""
    echo "usage:     . $0 rootfs_dir repo_dir"
    echo ""
    echo "#For example: If you want to install rpms from x86"
    echo "     #ls /home/yocto/workdir/dnf/oe-repo/rpm"
    echo "     i586  noarch  qemux86"
    echo ""
    echo "#You should use the following command to set your dnf environment"
    echo "      . $0 /home/yocto/rootfs /home/yocto/workdir/dnf/oe-repo"
    echo ""
    exit 0
fi

if [ ! -d $HIDDEN_ROOTFS ]; then
    echo " $HIDDEN_ROOTFS is not exist. mkdir $HIDDEN_ROOTFS. "
    mkdir -p $HIDDEN_ROOTFS
fi
}

#create repodata for rpm packages.
Create_repo () {
    if [ ${REPODIR:0:4} = "http" ];then
        echo "This is a remote repo!"
    else
        if [ ! -d $REPO_DIR ]; then
            echo "Error! $REPO_DIR is not exist. Please Check your rpm repo! "
            exit 0
        fi
        echo "Creating repo ..."
        if [ -f $REPO_DIR/comps.xml ]; then
            createrepo_c.real --update -q -g comps.xml $REPO_DIR
        else
            createrepo_c.real --update -q $REPO_DIR
        fi
    fi
}

travFolder () { 
    cd $1
    #echo $flist
    for f in `ls`
    do
        if [ "$f" = "repodata" ];then
           continue 
        fi
        if test -d $f;then
            travFolder $f
        else
            if [ "${f##*.}"x = "rpm"x ];then
                line=`echo "$f" | sed -r 's/.*\.(.*)\.rpm/\1/'`
                if [ "$line" != "all" ] && [ "$line" != "any" ] && [ "$line" != "noarch" ] && [ "$line" != "${ARCH}" ] && [ "$line" != "${MACHINE_ARCH}" ]; then
                    grep -w "$line" $HIDDEN_ROOTFS/etc/dnf/vars/arch > /dev/null
                    if [ $? -ne 0 ]; then
                        echo -n "$line:" >> $HIDDEN_ROOTFS/etc/dnf/vars/arch
                    fi
                fi
            fi
            continue
        fi
    done
    cd - 
}

Config_dnf () {
    #necessary dnf config
    if [ ! -d $HIDDEN_ROOTFS/etc/dnf ]; then
        mkdir -p $HIDDEN_ROOTFS/etc/dnf
        touch $HIDDEN_ROOTFS/etc/dnf/dnf-host.conf
    fi
    
    #clean the original content in dnf.conf file
    echo "[main]" > $HIDDEN_ROOTFS/etc/dnf/dnf-host.conf
    #Add config_path in dnf.conf file
    echo "spdx_repodir=$SPDXREPODIR" >> $HIDDEN_ROOTFS/etc/dnf/dnf-host.conf
    echo "spdx_download=$SPDXDIR" >> $HIDDEN_ROOTFS/etc/dnf/dnf-host.conf
    echo "srpm_repodir=$SRPMREPODIR" >> $HIDDEN_ROOTFS/etc/dnf/dnf-host.conf
    echo "srpm_download=$SRPMDIR" >> $HIDDEN_ROOTFS/etc/dnf/dnf-host.conf
    echo "rpm_repodir=$RPMREPODIR" >> $HIDDEN_ROOTFS/etc/dnf/dnf-host.conf
    echo "rpm_download=$RPMDIR" >> $HIDDEN_ROOTFS/etc/dnf/dnf-host.conf
    
    if [ ! -d $HIDDEN_ROOTFS/etc/dnf/vars ]; then
        mkdir -p $HIDDEN_ROOTFS/etc/dnf/vars
        echo -n "${MACHINE_ARCH}:${ARCH}:" >> $HIDDEN_ROOTFS/etc/dnf/vars/arch
        echo "Scanning repo ..."
        travFolder $REPO_DIR
    fi
    sed -i "s/:$/\n/g" $HIDDEN_ROOTFS/etc/dnf/vars/arch
}

Config_rpm () {
#necessary rpm config
if [ ! -d $HIDDEN_ROOTFS/etc/rpm ] || [ ! -f $HIDDEN_ROOTFS/etc/rpm/platform ]; then
    mkdir -p $HIDDEN_ROOTFS/etc/rpm
    echo "${MACHINE_ARCH}-pc-linux" > $HIDDEN_ROOTFS/etc/rpm/platform
fi

if [ ! -f $HIDDEN_ROOTFS/etc/rpmrc ]; then
    echo -n "arch_compat: ${MACHINE_ARCH}: all any noarch ${ARCH} ${MACHINE_ARCH}" > $HIDDEN_ROOTFS/etc/rpmrc
    for line in `ls $REPO_DIR/rpm`;do
        if [ "$line" != "all" ] && [ "$line" != "any" ] && [ "$line" != "noarch" ] && [ "$line" != "${ARCH}" ] && [ "$line" != "${MACHINE_ARCH}" ]; then
            echo -n " $line" >> $HIDDEN_ROOTFS/etc/rpmrc
        fi
    done
    sed -i "s/:$//g" $HIDDEN_ROOTFS/etc/rpmrc
fi
}

#Start from here
Export_env
source $WORKDIR/.env-dnf 
Check_para
Create_repo
Config_dnf
