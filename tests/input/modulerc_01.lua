-- default version of Java 1.8
module_version("Java/1.8.0_281", "1.8")
-- VERSION SWAPS FOR IB MODULES
local arch_suffix=os.getenv("VSC_ARCH_SUFFIX") or ""
if ( arch_suffix == "-ib") then
    module_version("UCX/1.8.0-GCCcore-9.3.0-ib", "1.8.0-GCCcore-9.3.0")
end
hide_version("UCX/1.8.0-GCCcore-9.3.0-ib")
-- END OF VERSION SWAPS FOR IB MODULES
-- hide all GCC v4.x
hide_version("GCCcore/4")
