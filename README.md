# 1. Introduction
***
Dandified Yum (DNF) is the next upcoming major version of [Yum](http://yum.baseurl.org/). It does package management using [RPM](http://rpm.org/), [libsolv](https://github.com/openSUSE/libsolv) and [hawkey](https://github.com/rpm-software-management/hawkey) libraries. For metadata handling and package downloads it utilizes [librepo](https://github.com/tojaj/librepo). To process and effectively handle the comps data it uses [libcomps](https://github.com/midnightercz/libcomps).

From yocto2.3, rpm5 and smart are replaced by rpm4 and dnf. So this README is for yocto 2.3 ~ Now.

# 2. Overview
***
Since existing dnf can not be used on host(e.g. a x86 PC with Linux), we developed dnf-host. The following functions have been developed.
  1. Add new command dnf-host to make dnf to work on host 
  2. Dnf TUI functions
  3. Manage SPDX files
  4. Manage SRPM files

Now, dnf can be used both on host and target(e.g. an arm board) environment.

# 3. Usage of dnf

## 3.1 On host

### 3.1.1 Prepare

  Make sure you have prepared the following:
  * toolchain(mandatory)
  * rpm packages(mandatory)
  * sprpm packages(optional)
  * spdx files(optional)
  
  Note
  * SELinux must be closed.
  * Run as a non-root user that has sudo authority.

#### (1) install the cross-development toolchain(e.g. for i586: poky-glibc-x86_64-meta-toolchain-i586-toolchain-2.4.1.sh) and set up environment of toolchain.
```
      $ sh poky-glibc-x86_64-meta-toolchain-i586-toolchain-2.4.1.sh
      $ . /opt/poky/2.4.1/environment-setup-i586-poky-linux		
      Note
        - When you compilering toochain, make sure you have patched the patch of patches-yocto.
        - If you change a terminal, you should source toolchain again.
```
#### (2) rpm packages
&emsp;&emsp;Created by yocto, for example, one repo director in rpm format for x86 likes as following:
```
      $ ls /home/test/workdir/dnf_test/oe_repo/
        rpm
      $ ls /home/test/workdir/dnf_test/oe_repo/rpm/
        i586  noarch  qemux86
```
#### (3) srpm packages
&emsp;&emsp;If you enable "archiver " in you Yocto buid environment, you can get srpm packages for every OSS you build.
```			
      $ ls /home/test/workdir/dnf_test/srpm_repo
        bash-4.3.30-r0.src.rpm
        ......
```

     
#### (4) spdx files (https://github.com/dl9pf/meta-spdxscanner)
&emsp;&emsp;Please reference to the README of meta-spdxscanner to get spdx files bu Yocto.
```		
      $ ls /home/test/workdir/dnf_test/spdx_repo
        bash-4.3.30.spdx
        ......
```

### 3.1.2 Initialize

If you want to ctreate an empty rootfs, you have to run "dnf-host init".

```
  $ dnf-host init
  The repo directory: (default:/home/test/workdir/dnf_test/oe_repo).
  Is this ok?[y/N]:
  y
  repo directory: /home/test/workdir/dnf_test/oe_repo
  The rootfs destination directory: (default: /opt/ubq/devkit/x86/).
  Is this ok?[y/N]:
  y
  rootfs destination directory: /opt/ubq/devkit/x86/
  The SPDX repo directory: (default: file:///home/test/workdir/dnf_test/spdx_repo).
  Is this ok?[y/N]:
  y
  SPDX repo directory: file:///home/test/workdir/dnf_test/spdx_repo
  The SPDX file destination directory: (default: /home/test/workdir/dnf_test/spdx_download).
  Is this ok?[y/N]:
  y
  SPDX file destination directory: /home/test/workdir/dnf_test/spdx_download
  The SRPM repo directory: (default: file:///home/test/workdir/dnf_test/srpm_repo).
  Is this ok?[y/N]:
  y
  SRPM repo directory: file:///home/test/workdir/dnf_test/srpm_repo
  The SRPM file destination directory: (default: /home/test/workdir/dnf_test/srpm_download).
  Is this ok?[y/N]:
  y
  SRPM file destination directory: /home/test/workdir/dnf_test/srpm_download
  Note
    - Because dnf-host reads configuration fron `pwd`, please make sure the following steps are in the same directory same as you run init.
    - Dnf-host will save what you have done continuous until you run init again.
```

After init, then, you can manage packages by TUI or command line.

### 3.1.3 Manage packages in TUI


  Dnf TUI(textual user interface) Function is developed for dnf-host. With TUI, it is easy to customize rootfs of target.
  <br/>Note
  <br/>&emsp;Please make sure your screen is at least 24 lines and 80 columns.
  
  By the following command you can enter the main interface of TUI.
  
  ```
  [test@localhost dnf_test]$ dnf-host tui
        ┌────────────────────────┤ Select your operation ├─────────────────────────┐
        │                                                                          │
        │ Install                                                                  │
        │ Remove                                                                   │
        │ Upgrade                                                                  │
        │ Create source archive                                                    │
        │ Create spdx archive                                                      │
        │                                                                          │
        │                                                                          │
        │                                                                          │
        │                                                                          │
        │                                                                          │
        │                                                                          │
        │                                                                          │
        │                                                                          │
        │                                                                          │
        │                                                                          │
        │ ------------------------------------------------------------------------ │
        │ SPACE/ENTER:select  I:Info  X:eXit                                       │
        └──────────────────────────────────────────────────────────────────────────┘
```

#### (1) dnf-host TUI can help you filter GPLv3.
&emsp;&emsp;If you select "install" in above, dnf-host will ask you whether you want to install packages 
	 which license is GPLv3.
```	 
	   
                  ┌───────────────┤ License ├────────────────┐
                  │                                          │
                  │                                          │
                  │  Do you want to display GPLv3 packages?  │
                  │                                          │
                  │                                          │
                  │ ---------------------------------------- │
                  │ Y:yes  N:no                              │
                  └──────────────────────────────────────────┘
				  
       - No  : GPLv3 packages will not be selected and not display in the next step.
       - Yes : GPLv3 packages can be selected as same as the other packages.
 ```     
 
 #### (2) install
```
        ┌────────────────────────────┤ Select package ├────────────────────────────┐
        │                                                                          │
        │ [I] acl                                                                  │
        │ [I] attr                                                                 │
        │ [*] base-files                                                           │
        │ [ ] base-passwd                                                          │
        │ [ ] base-passwd-update                                                   │
        │ [ ] bash                                                                 │
        │ [ ] bash-bashbug                                                         │
        │ [ ] bash-completion                                                      │
        │ [ ] bash-completion-extra                                                │
        │ [ ] bash-loadable                                                        │
        │ [ ] bc                                                                   │
        │ [ ] bind                                                                 │
        │ ------------------------------------------------------------------------ │
        │ All Packages [3935]    Installed Packages [0]    Selected Packages [0]   │
        │ ------------------------------------------------------------------------ │
        │ SPACE/ENTER:select/unselect  A:select/unselect All  R:seaRch N:Next      │
        │ B:Back  I:Info  X:eXit                                                   │
        └──────────────────────────────────────────────────────────────────────────┘

       
         Note
            - []  Means the package has not been selected or installed. If you want to install it, you can
                  select it by pressing space or enter.
            - [*] Means the package has been selcted and will be installed. If you don't want to install it,
                  you can cancel by pressing space or enter.
            - [I] Means the package has been installed in your rootfs.
			
			- Next: If you press "N" or "n" in the interface, it will go to the next step.
```

#### (3) customize packages type
&emsp;&emsp;You can select the package type that you want to install into rootfs.
```
        ┌───────────────────┤ Customize special type packages ├────────────────────┐
        │                                                                          │
        │ locale [ ]                                                               │
        │ dev [ ]                                                                  │
        │ doc [ ]                                                                  │
        │ dbg [ ]                                                                  │
        │ staticdev [ ]                                                            │
        │ ptest [ ]                                                                │
        │                                                                          │
        │                                                                          │
        │                                                                          │
        │                                                                          │
        │                                                                          │
        │                                                                          │
        │                                                                          │
        │ ------------------------------------------------------------------------ │
        │ SPACE/ENTER:select/unselect  N:Next  B:Back  I:Info  X:eXit              │
        └──────────────────────────────────────────────────────────────────────────┘

        Note
          You can get details about the package type by pressing "I" or "i".
```
#### (4) Confirm install
&emsp;&emsp;If you select "N"/"n" in the "license" interface, but there is GPLV3 ppackages in the dependences,
<br>&emsp;&emsp;A dialog box will ask your decision.
```	    
          ┌────────────────────────┤ GPLv3 that be depended ├────────────────────────┐
          │                                                                          │
          │ bash                                                                     │
          │                                                                          │
          │                                                                          │
          │                                                                          │
          │                                                                          │
          │                                                                          │
          │                                                                          │
          │                                                                          │
          │                                                                          │
          │                                                                          │
          │                                                                          │
          │                                                                          │
          │                                                                          │
          │ ------------------------------------------------------------------------ │
          │ These GPLv3 packages are depended, do you want to install them? (y/n)    │
          └──────────────────────────────────────────────────────────────────────────┘

         Otherwise, you will enter the comfirm interface.
		 
                  ┌───────────┤ Confirm install ├────────────┐
                  │                                          │
                  │                                          │
                  │  Do you want to begin installation?      │
                  │                                          │
                  │                                          │
                  │ ---------------------------------------- │
                  │ Y:yes  N:no                              │
                  └──────────────────────────────────────────┘
	    After you confirming your customization, the installation will begin.
```
#### (5) Remove
&emsp;&emsp;You can choose the package that you want to upgrade after enter "Remove" in main interface..
```
        ┌────────────────────────────┤ Select package ├────────────────────────────┐
        │                                                                          │
        │ [-] libc6                                                                │
        │ [-] ncurses-terminfo-base                                                │
        │ [-] acl                                                                  │
        │ [ ] libacl1                                                              │
        │ [ ] libtinfo5                                                            │
        │ [ ] base-files                                                           │
        │ [ ] update-alternatives-opkg                                             │
        │ [ ] bash                                                                 │
        │ [ ] libattr1                                                             │
        │                                                                          │
        │                                                                          │
        │                                                                          │
        │ ------------------------------------------------------------------------ │
        │ All Packages [9]    Selected Packages [0]                                │
        │ ------------------------------------------------------------------------ │
        │ SPACE/ENTER:select/unselect  A:select/unselect All  R:seaRch N:Next      │
        │ B:Back  I:Info  X:eXit                                                   │
        └──────────────────────────────────────────────────────────────────────────┘
```
#### (6) Upgrade
&emsp;&emsp;You can choose the package that you want to upgrade after enter "upgrade" in main interface.
```
        ┌────────────────────────────┤ Select package ├────────────────────────────┐
        │                                                                          │
        │ [U] base-files                                                           │
        │ [U] bash                                                                 │
        │ [U] ncurses-terminfo-base                                                │
        │ [ ] libtinfo5                                                            │
        │ [ ] update-alternatives-opkg                                             │
        │ [ ] libc6                                                                │
        │                                                                          │
        │                                                                          │
        │                                                                          │
        │                                                                          │
        │                                                                          │
        │                                                                          │
        │ ------------------------------------------------------------------------ │
        │ All Packages [6]    Selected Packages [0]                                │
        │ ------------------------------------------------------------------------ │
        │ SPACE/ENTER:select/unselect  A:select/unselect All  R:seaRch N:Next      │
        │ B:Back  I:Info  X:eXit                                                   │
        └──────────────────────────────────────────────────────────────────────────┘
        Note
          - []  Means the package could be upgrade and has not been selected. If you want to upgrade it, you can
                select it by pressing space or enter.
          - [U] Means the package has been selcted ,installed and will be upgraded.
```
#### (7) manage source archive & spdx archive
&emsp;&emsp;You can choose the package that you want to upgrade after enter "Create spdx archive" or "Create spdx archive" in main interface.
```	  
        ┌────────────────────────────┤ Select package ├────────────────────────────┐
        │                                                                          │
        │ [S] base-files                                                           │
        │ [S] bash                                                                 │
        │ [ ] ncurses-terminfo-base                                                │
        │ [ ] libtinfo5                                                            │
        │ [ ] update-alternatives-opkg                                             │
        │ [ ] libc6                                                                │
        │                                                                          │
        │                                                                          │
        │                                                                          │
        │                                                                          │
        │                                                                          │
        │                                                                          │
        │ ------------------------------------------------------------------------ │
        │ All Packages [6]    Selected Packages [0]                                │
        │ ------------------------------------------------------------------------ │
        │ SPACE/ENTER:select/unselect  A:select/unselect All  R:seaRch N:Next      │
        │ B:Back  I:Info  X:eXit                                                   │
        └──────────────────────────────────────────────────────────────────────────┘
        Note
          - []  Means the package has not been selected.
          - [S] Means the package has been selcted ,installed and will be used to created.
```
### 3.1.4 Manage packages by command line

After init, you can use dnf-host to manage packages such as using dnf in other Distro (e.g. Fedora)". More information please reference to https://fedoraproject.org/wiki/DNF?rd=Dnf.

e.g.
```
$ dnf-host info bash
$ dnf-host install bash
......

```

### 3.1.5 manage srpm packages & spdx files

#### 3.1.5.1 manage srpm or spdx when you run "dnf-host install" by add the following option:

   (1) --with-srpm
```
      [test@localhost dnf_test]$ dnf-host install --with-srpm bash 
      ......

      [test@localhost dnf_test]$ ls srpm_download/
      bash-4.3.30.src.rpm
```        
   (2) --with-spdx
```
      [test@localhost dnf_test]$ dnf-host install --with-spdx bash 
      ......

      [test@localhost dnf_test]$ ls spdx_download/
      bash-4.3.30.spdx
```

#### 3.1.5.2 manage srpm or spdx only

If you want to manage srpm or spdx files without installation, you can use the subcommand as following:  
  (1) fetchsrpm
```
      [test@localhost dnf_test]$ dnf-host fetchsrpm bash 
      ......
      [test@localhost dnf_test]$ ls srpm_download/
      bash-4.3.30.src.rpm
```
  (2) fetchspdx
<br>&emsp;&emsp;fetchsrpm is the same as fetchspdx
       
```	
      [test@localhost dnf_test]$ dnf-host fetchspdx bash 
      ......
      [test@localhost dnf_test]$ ls spdx_download/
      bash-4.3.30.spdx
```

## 3.2 On target

### 3.2.1  Configuration

#### (1) configure rpm repo (mandatory)  
&emsp;&emsp;The same as using dnf on the other Distro (e.g. Fedora), you have to configure your rpm repo in /etc/yum.repos.d/Base.repo.

#### (2) configure srpm and spdx (optional)  
&emsp;&emsp;If you want to manage srpm or spdx files on target, you have to configure repository in /etc/dnf/dnf-host.conf.  
&emsp;&emsp;For example:
```
        [root@localhost target]# cat /etc/dnf/dnf-host.conf
        [main]
        gpgcheck=1
        installonly_limit=3
        clean_requirements_on_remove=True
        spdx_repodir=http://192.168.65.144/oe_repo/spdx_repo
        spdx_download=/home/root/spdx_download
        srpm_repodir=http://192.168.65.144/oe_repo/srpm_repo
        srpm_download=/home/root/srpm_download
```

### 3.2.2 Usage

The same as dnf-host.

# 4. Documentation
***
If you want to know more knowledge about dnf, read the documentation of dnf.
The DNF package distribution contains man pages, dnf(8) and dnf.conf(8). It is also possible to [read the DNF documentation](http://dnf.readthedocs.org/)online, the page includes API documentation. There's also a [wiki](https://github.com/rpm-software-management/dnf/wiki) meant for contributors to DNF and related projects.
