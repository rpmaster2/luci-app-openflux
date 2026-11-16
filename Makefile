# SPDX-License-Identifier: MIT
#
# Build with the OpenWrt SDK:
#
#   mkdir -p package/luci-app-openflux
#   cp -r . package/luci-app-openflux
#   make package/luci-app-openflux/compile V=s
#
# The resulting ipk lands in bin/packages/*/base/ or bin/packages/*/luci/.
#
# For a quick build without the SDK use: python3 build-ipk.py

include $(TOPDIR)/rules.mk

PKG_NAME:=luci-app-openflux
PKG_VERSION:=$(shell cat $(CURDIR)/VERSION 2>/dev/null | tr -d '\r\n')
PKG_RELEASE:=1
PKG_LICENSE:=MIT

LUCI_TITLE:=LuCI app for OpenFlux client
LUCI_DESCRIPTION:=Manage OpenFlux client profiles and run a single selected profile
LUCI_DEPENDS:=+luci-base
LUCI_PKGARCH:=all

include $(TOPDIR)/feeds/luci/luci.mk

# call BuildPackage - OpenWrt buildroot signature
