# tui.py
# Tgui CLI command.
#
# Copyright (C) 2018 FUJITSU LIMITED
#
from __future__ import absolute_import
from __future__ import unicode_literals
from dnf.cli import commands
from dnf.cli.option_parser import OptionParser
from dnf.i18n import _
from itertools import chain
import dnf.subject

import dnf.exceptions
import hawkey
import logging

from dnf.cli.window import *
import sys, os, copy, textwrap, snack, string, time, re, shutil
from snack import *

import dnf.cli.demand
import dnf.cli.option_parser
import dnf.cli.commands.shell
import dnf.conf
import dnf.conf.parser
import dnf.conf.substitutions
import dnf.const
import dnf.exceptions
import dnf.cli.format
import dnf.logging
import dnf.plugin
import dnf.persistor
import dnf.rpm
import dnf.util
import dnf.cli.utils
import dnf.yum.misc

_TXT_ROOT_TITLE = "Package Installer"

Install_actions = [("Install", "Choose it to install packages."), \
                   ("Remove", "Choose it to remove packages"), \
                   ("Upgrade", "Choose it to upgrade packages"), \
                   ("Create source archive", "Choose it to create source archive"), \
                   ("Create spdx archive", "Choose it to Create SPDX archive") \
                  ]

ACTION_INSTALL     = 0
ACTION_REMOVE      = 1
ACTION_UPGRADE     = 2
ACTION_GET_SOURCE  = 3
ACTION_GET_SPDX    = 4

CONFIRM_EXIT       = 0
CONFIRM_INSTALL    = 1
CONFIRM_LICENSE    = 2
CONFIRM_REMOVE     = 3
CONFIRM_UPGRADE    = 4
CONFIRM_GET_SOURCE = 5
CONFIRM_GET_SPDX   = 6

ATTENTON_NONE           = 0
ATTENTON_HAVE_UPGRADE   = 1
ATTENTON_NONE_UPGRADE   = 2

logger = logging.getLogger('dnf')

class TuiCommand(commands.Command):
    """A class containing methods needed by the cli to execute the
    tui command.
    """

    aliases = ('tui',)
    summary = _('Enter tui interface.')

    def configure(self):
        self.cli.demands = dnf.cli.commands.shell.ShellDemandSheet()

    def run(self, command=None, argv=None):
        logger.debug("Enter tui interface.")
        self.PKGINSTDispMain()

    def run_dnf_command(self, s_line):
        """Execute the subcommand you put in.
        """
        opts = self.cli.optparser.parse_main_args(s_line)
        cmd_cls = self.cli.cli_commands.get(opts.command)
        cmd = cmd_cls(self)
        try:
            opts = self.cli.optparser.parse_command_args(cmd, s_line)
            cmd.cli = self.cli
            cmd.cli.demands = copy.deepcopy(self.cli.demands)
            cmd.configure()
            cmd.run()
        except:
            pass

    def PKGINSTDispMain(self):
        STAGE_INSTALL_TYPE = 1
        STAGE_PKG_TYPE     = 2
        STAGE_CUST_LIC     = 3
        STAGE_PACKAGE      = 4
        STAGE_PACKAGE_SPEC = 5
        STAGE_PROCESS      = 6
        
        screen = None
        no_gpl3 = False
        
        pkgnarrow = 'all'
        patterns = None
        installed_available = False
        reponame = None
        #----dnf part-------
        try:
            ypl = self.base.returnPkgLists(
                pkgnarrow, patterns, installed_available, reponame)
        except dnf.exceptions.Error as e:
            return 1, [str(e)]
        else:
            if len(ypl.available + ypl.installed) < 1:
                print ("Error! No packages!")
                sys.exit(0)
            screen = StartHotkeyScreen(_TXT_ROOT_TITLE)
            if screen == None:
                sys.exit(1)
            install_type = ACTION_INSTALL
            stage = STAGE_INSTALL_TYPE
 
            def __init_pkg_type():
                pkgTypeList = []
            
                pkgType_locale = pkgType("locale", False, "If select, you can see/select *-locale/*-localedata packages in the next step.")
                pkgTypeList.append(pkgType_locale)
                pkgType_dev = pkgType("dev", False, "If select, you can see/select *-dev packages in the next step.")
                pkgTypeList.append(pkgType_dev)
                pkgType_doc = pkgType("doc", False, "If select, you can see/select *-doc packages in the next step.")
                pkgTypeList.append(pkgType_doc)
                pkgType_dbg = pkgType("dbg", False, "If select, you can see/select *-dbg packages in the next step.")
                pkgTypeList.append(pkgType_dbg)
                pkgType_staticdev = pkgType("staticdev", False, "If select, you can see/select *-staticdev packages in the next step.")
                pkgTypeList.append(pkgType_staticdev)
                pkgType_ptest = pkgType("ptest", False, "If select, you can see/select *-ptest packages in the next step.")
                pkgTypeList.append(pkgType_ptest)

                return pkgTypeList

            pkgTypeList = __init_pkg_type()
            selected_pkgs = []
            selected_pkgs_spec = []
            pkgs_spec = []
            src_path=""
            output_path=""
            while True:
                #==============================
                # select install type
                #==============================
                if stage == STAGE_INSTALL_TYPE:
 
                    install_type = PKGINSTActionWindowCtrl(screen, Install_actions, install_type)

                    if install_type == ACTION_GET_SOURCE or install_type == ACTION_GET_SPDX:
                        stage = STAGE_PACKAGE
                        continue
                    else:
                        stage = STAGE_PACKAGE

                    selected_pkgs = []
                    selected_pkgs_spec = []
                    pkgs_spec = []

                    if install_type == ACTION_INSTALL:
                        result = HotkeyExitWindow(screen, confirm_type=CONFIRM_LICENSE)
                        if result == "y":
                            no_gpl3 = False
                        else:
                            no_gpl3 = True
                    else:
                        no_gpl3 = False


                #==============================
                # select package
                #==============================
                elif stage == STAGE_PACKAGE:
                    (result, selected_pkgs, pkgs_spec) = self.PKGINSTWindowCtrl(screen, install_type, None, no_gpl3, \
                                                                                None, selected_pkgs)
                    if result == "b":
                        # back
                        stage = STAGE_INSTALL_TYPE

                    elif result == "n":
                        if install_type == ACTION_INSTALL:
                            stage = STAGE_PKG_TYPE
                        else:
                            #confirm if or not continue process function
                            if   install_type == ACTION_REMOVE     : confirm_type = CONFIRM_REMOVE
                            elif install_type == ACTION_UPGRADE    : confirm_type = CONFIRM_UPGRADE
                            elif install_type == ACTION_GET_SOURCE : confirm_type = CONFIRM_GET_SOURCE
                            elif install_type == ACTION_GET_SPDX   : confirm_type = CONFIRM_GET_SPDX

                            hkey = HotkeyExitWindow(screen, confirm_type)
                            if hkey == "y":
                                stage = STAGE_PROCESS
                            elif hkey == "n":
                                stage = STAGE_PACKAGE

                #==============================
                # select package type
                #==============================
                elif stage == STAGE_PKG_TYPE:
                    (result, pkgTypeList) = PKGTypeSelectWindowCtrl(screen, pkgTypeList)
                    if result == "b":
                        # back
                        stage = STAGE_PACKAGE
                    elif result == "n":
                        stage = STAGE_PACKAGE_SPEC
                #==============================
                # select special packages(local, dev, dbg, doc) 
                #==============================
                elif stage == STAGE_PACKAGE_SPEC:
                    (result, selected_pkgs_spec, pkgs_temp) = self.PKGINSTWindowCtrl(screen, install_type, pkgTypeList, \
                                                                                no_gpl3, pkgs_spec, selected_pkgs_spec)
                    if result == "b":
                        # back
                        stage = STAGE_PKG_TYPE
                    elif result == "k":
                        stage = STAGE_PKG_TYPE
                    elif result == "n":
                        stage = STAGE_PROCESS

                # ==============================
                # Process function
                # ==============================
                elif stage == STAGE_PROCESS:
                    if install_type == ACTION_GET_SOURCE or install_type == ACTION_GET_SPDX:
                        if screen != None:
                            StopHotkeyScreen(screen)
                            screen = None
                        if install_type == ACTION_GET_SOURCE:
                            srcdir_path = self.base.conf.srpm_repodir
                            destdir_path = self.base.conf.srpm_download
                            dnf.cli.utils.fetchSPDXorSRPM('srpm', selected_pkgs, srcdir_path, destdir_path)
                        elif install_type == ACTION_GET_SPDX:
                            srcdir_path = self.base.conf.spdx_repodir
                            destdir_path = self.base.conf.spdx_download
                            dnf.cli.utils.fetchSPDXorSRPM('spdx', selected_pkgs, srcdir_path, destdir_path)
                        break
                    else:
                        for pkg in selected_pkgs:           #selected_pkgs
                            if install_type == ACTION_INSTALL:
                                s_line = ["install", pkg.name]
                            elif install_type == ACTION_REMOVE:
                                s_line = ["remove", pkg.name]
                            elif install_type == ACTION_UPGRADE:
                                s_line = ["upgrade", pkg.name]
                            self.run_dnf_command(s_line)

                        if install_type == ACTION_INSTALL:  #selected_pkgs_spec
                            for pkg in selected_pkgs_spec:
                                s_line = ["install", pkg.name]
                                self.run_dnf_command(s_line)

                        if no_gpl3:
                            #obtain the transaction
                            self.base.resolve(self.cli.demands.allow_erasing)
                            install_set = self.base.transaction.install_set

                            result = self.showChangeSet(screen, install_set)
                            #continue to install
                            if result == "y":
                                if install_type == ACTION_INSTALL:
                                    confirm_type = CONFIRM_INSTALL

                                hkey = HotkeyExitWindow(screen, confirm_type)
 
                                if hkey == "y":
                                    if screen != None:
                                        StopHotkeyScreen(screen)
                                        screen = None
                                    if install_type != ACTION_REMOVE:
                                        self.base.conf.assumeyes = True
                                    break
                                elif hkey == "n":
                                    stage = STAGE_PKG_TYPE
                            #don't want to install GPLv3 that depended by others
                            else:
                                stage = STAGE_PKG_TYPE
                        else:
                            if screen != None:
                                StopHotkeyScreen(screen)
                                screen = None
                                if install_type != ACTION_REMOVE:
                                    self.base.conf.assumeyes = True
                            break

            if screen != None:
                StopHotkeyScreen(screen)
                screen = None

    def _DeleteUpgrade(self,packages=None,display_pkgs=[]):
        haveUpgrade=False
        for i, pkg in enumerate(display_pkgs[:-1]):
            for pkg_oth in display_pkgs[i+1:]:
                if pkg.name==pkg_oth.name:
                    haveUpgrade=True
                    break
            if haveUpgrade :
                break
        ctn=0
        if(haveUpgrade):
            for pkg in packages:
                if  (not pkg.installed) and (pkg in display_pkgs):
                    ctn+=1
                    display_pkgs.remove(pkg)
        return haveUpgrade

    def PKGINSTWindowCtrl(self, screen, install_type, pkgTypeList, no_gpl3, packages=None, selected_pkgs=[]):
        STAGE_SELECT = 1
        STAGE_PKG_TYPE = 2
        STAGE_BACK   = 3
        STAGE_INFO   = 4
        STAGE_EXIT   = 5
        STAGE_SEARCH = 6
        STAGE_NEXT = 7

        iTargetSize = 0
        iHostSize = 0

        searched_ret = [] 
        pkgs_spec = []
        position = 0
        search_position = 0
        check = 0
        stage = STAGE_SELECT
        search = None

        pkgnarrow = 'all'
        patterns = None
        installed_available = False
        reponame = None

        try:
            ypl = self.base.returnPkgLists(
                pkgnarrow, patterns, installed_available, reponame)
        except dnf.exceptions.Error as e:
            return 1, [str(e)]
 
        if pkgTypeList == None:
            pkg_available = copy.copy(ypl.available)
            pkg_installed = copy.copy(ypl.installed)
            packages = ypl.installed + ypl.available
            display_pkgs = pkg_installed + pkg_available
            sorted(packages)
            sorted(display_pkgs)
        else:
            pkg_available = copy.copy(ypl.available)
            pkg_installed = copy.copy(ypl.installed)
            packages = ypl.installed + ypl.available
            display_pkgs = pkg_installed + pkg_available
            #display_pkgs = copy.copy(packages)

        if no_gpl3:
            for pkg in (ypl.installed + ypl.available):
                license = pkg.license
                if license:
                    if "GPLv3" in license:
                        display_pkgs.remove(pkg)
            packages = copy.copy(display_pkgs) #backup all pkgs

        if pkgTypeList != None:
            for pkyType in pkgTypeList:
                if pkyType.name == "locale":
                    if not pkyType.status:
                        pkyType_locale = False
                    else:
                        pkyType_locale = True
                elif pkyType.name == "dev":
                    if not pkyType.status:
                        pkyType_dev = False
                    else:
                        pkyType_dev = True
                elif pkyType.name == "doc":
                    if not pkyType.status:
                        pkyType_doc = False
                    else:
                        pkyType_doc = True
                elif pkyType.name == "dbg":
                    if not pkyType.status:
                        pkyType_dbg = False
                    else:
                        pkyType_dbg = True
                elif pkyType.name == "staticdev":
                    if not pkyType.status:
                        pkyType_staticdev = False
                    else:
                        pkyType_staticdev = True
                elif pkyType.name == "ptest":
                    if not pkyType.status:
                        pkyType_ptest = False
                    else:
                        pkyType_ptest = True

            if pkyType_locale or pkyType_dev or pkyType_doc or pkyType_dbg or pkyType_staticdev or pkyType_ptest:
                #Don't show doc and dbg packages
                for pkg in packages:
                    if "-locale-" in pkg.name:
                        if not pkyType_locale:
                            display_pkgs.remove(pkg)
                    elif "-localedata-" in pkg.name:
                        if not pkyType_locale:
                            display_pkgs.remove(pkg)
                    elif pkg.name.endswith('-dev'):
                        if not pkyType_dev:
                            display_pkgs.remove(pkg)
                    elif pkg.name.endswith('-doc'):
                        if not pkyType_doc:
                            display_pkgs.remove(pkg)
                    elif pkg.name.endswith('-dbg'):
                        if not pkyType_dbg:
                            display_pkgs.remove(pkg)
                    elif pkg.name.endswith('-staticdev'):
                        if not pkyType_staticdev:
                            display_pkgs.remove(pkg)
                    elif pkg.name.endswith('-ptest'):
                        if not pkyType_ptest:
                            display_pkgs.remove(pkg)
            else:
                display_pkgs = []

            if (install_type==ACTION_REMOVE) or (install_type==ACTION_UPGRADE) or (install_type==ACTION_GET_SOURCE) \
                                                                               or (install_type==ACTION_GET_SPDX) :
                for pkg in packages:
                    if pkg not in ypl.installed:
                        if pkg in display_pkgs:
                            display_pkgs.remove(pkg)

            elif install_type == ACTION_INSTALL:
                if(self._DeleteUpgrade(packages,display_pkgs)):
                    hkey = HotkeyAttentionWindow(screen, ATTENTON_HAVE_UPGRADE)

            if len(display_pkgs) == 0:
                if not no_gpl3:
                    if install_type == ACTION_INSTALL     :
                        confirm_type = CONFIRM_INSTALL
                        hkey = HotkeyExitWindow(screen, confirm_type)
                        if hkey == "y":
                            return ("n", selected_pkgs, packages)
                        elif hkey == "n":
                            return ("k", selected_pkgs, packages)
                    else:
                        hkey=HotkeyAttentionWindow(screen,ATTENTON_NONE)
                        return ("b", selected_pkgs, packages)
                else:
                    return ("n", selected_pkgs, packages)
        else:
            if install_type == ACTION_INSTALL :
                for pkg in packages:
                    if "-locale-" in pkg.name:
                        display_pkgs.remove(pkg)
                        pkgs_spec.append(pkg)
                    elif "-localedata-" in pkg.name:
                        display_pkgs.remove(pkg)
                        pkgs_spec.append(pkg)
                    elif pkg.name.endswith('-dev'):
                        display_pkgs.remove(pkg)
                        pkgs_spec.append(pkg)
                    elif pkg.name.endswith('-doc'):
                        display_pkgs.remove(pkg)
                        pkgs_spec.append(pkg)
                    elif pkg.name.endswith('-dbg'):
                        display_pkgs.remove(pkg)
                        pkgs_spec.append(pkg)
                    elif pkg.name.endswith('-staticdev'):
                        display_pkgs.remove(pkg)
                        pkgs_spec.append(pkg)
                    elif pkg.name.endswith('-ptest'):
                        display_pkgs.remove(pkg)
                        pkgs_spec.append(pkg)

                if(self._DeleteUpgrade(packages,display_pkgs)):
                    hkey = HotkeyAttentionWindow(screen, ATTENTON_HAVE_UPGRADE)

            else:
                for pkg in packages:
                    if pkg not in ypl.installed:
                        if pkg in display_pkgs:
                            display_pkgs.remove(pkg)
                display_pkgs = sorted(display_pkgs)

            if install_type == ACTION_UPGRADE:
                self.base.upgrade_all()
                self.base.resolve(self.cli.demands.allow_erasing)
                install_set = self.base.transaction.install_set
              
                display_pkgs = []
                for pkg in install_set:
                    display_pkgs.append(pkg)
                display_pkgs = sorted(display_pkgs)

                # clean the _transaction
                self.base.close()
                self.base._transaction = None

        if len(display_pkgs)==0:
            if install_type==ACTION_INSTALL:
                stage = STAGE_NEXT
            elif install_type==ACTION_UPGRADE:
                hkey = HotkeyAttentionWindow(screen, ATTENTON_NONE_UPGRADE)
                return ("b", selected_pkgs, packages)
            else:
                hkey = HotkeyAttentionWindow(screen, ATTENTON_NONE)
                return ("b", selected_pkgs, packages)

        while True:
            if stage == STAGE_SELECT:
                if search == None:
                    (hkey, position, pkglist) = PKGINSTPackageWindow(screen, \
                                                            display_pkgs, \
                                                            selected_pkgs, \
                                                            position, \
                                                            iTargetSize, \
                                                            iHostSize, \
                                                            search, \
                                                            install_type)
                else:
                    (hkey, search_position, pkglist) = PKGINSTPackageWindow(screen, \
                                                             searched_ret, \
                                                             selected_pkgs, \
                                                             search_position, \
                                                             iTargetSize, \
                                                             iHostSize, \
                                                             search, \
                                                             install_type)

                if hkey == "n":
                    stage = STAGE_NEXT
                elif hkey == "b":
                    stage = STAGE_BACK
                elif hkey == "i":
                    stage = STAGE_INFO
                elif hkey == "x":
                    stage = STAGE_EXIT
                elif hkey == 'r':
                    stage = STAGE_SEARCH
            elif stage == STAGE_NEXT:
                search = None
                #if in packages select Interface:
                if pkgTypeList == None:
                    return ("n", selected_pkgs, pkgs_spec)
                #if in special type packages(dev,doc,locale) select Interface:
                else:
                    if not no_gpl3:
                        if install_type == ACTION_INSTALL : confirm_type = CONFIRM_INSTALL

                        hkey = HotkeyExitWindow(screen, confirm_type)
                        if hkey == "y":
                            return ("n", selected_pkgs, packages)
                        elif hkey == "n":
                            stage = STAGE_SELECT
                    else:
                        return ("n", selected_pkgs, packages)
            elif stage == STAGE_BACK:
                if not search == None:
                    stage = STAGE_SELECT
                    search = None
                else:
                    return ("b", selected_pkgs, pkgs_spec)
            elif stage == STAGE_INFO:
                if not search == None:
                    PKGINSTPackageInfoWindow(screen, searched_ret[search_position])
                else:
                    PKGINSTPackageInfoWindow(screen, display_pkgs[position])
                stage = STAGE_SELECT
            elif stage == STAGE_EXIT:
                hkey = HotkeyExitWindow(screen)
                if hkey == "y":
                    if screen != None:
                        StopHotkeyScreen(screen)
                        screen = None
                    sys.exit(0)
                elif hkey == "n":
                    stage = STAGE_SELECT
            elif stage == STAGE_SEARCH:
                search_position = 0
                search = PKGINSTPackageSearchWindow(screen)
                if not search == None:
                    def __search_pkgs(keyword, pkgs):
                        searched_pgks = []
                        keyword = re.escape(keyword)
                        for pkg in pkgs:
                            if re.compile(keyword, re.IGNORECASE).search(pkg.name):
                                searched_pgks.append(pkg)
                        return searched_pgks
                    searched_ret = __search_pkgs(search, display_pkgs)
                    if len(searched_ret) == 0:
                        buttons = ['OK']
                        (w, h) = GetButtonMainSize(screen)
                        rr = ButtonInfoWindow(screen, "Message", "%s - not found." % search, w, h, buttons)
                        search = None
                stage = STAGE_SELECT

    def showChangeSet(self, screen, pkgs_set):
        gplv3_pkgs = []
        #pkgs = self.opts.pkg_specs
        for pkg in pkgs_set:
            license = pkg.license
            if license:
                if "GPLv3" in license:
                    gplv3_pkgs.append(pkg)
        if len(gplv3_pkgs) > 0:
            hkey = ConfirmGplv3Window(screen, gplv3_pkgs)
            if hkey == "y":
                return "y"
            elif hkey == "n":
                return "n"
        else:
            return "y"
