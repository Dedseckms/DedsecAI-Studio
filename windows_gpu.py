"""Driver-neutral Windows adapter inventory; shared RAM is never counted as VRAM."""
import ctypes as c
import os
import uuid


def adapters():
    if os.name != 'nt':return []
    class GUID(c.Structure):
        _fields_=[('data',c.c_ubyte*16)]
    class LUID(c.Structure):
        _fields_=[('low',c.c_uint32),('high',c.c_int32)]
    class Description(c.Structure):
        _fields_=[('name',c.c_wchar*128)]+[(n,c.c_uint32) for n in ('vendor','device','subsystem','revision')]+[(n,c.c_size_t) for n in ('video','system','shared')]+[('luid',LUID),('flags',c.c_uint32)]
    def method(obj,index,result,*args):
        table=c.cast(obj,c.POINTER(c.POINTER(c.c_void_p))).contents
        return c.WINFUNCTYPE(result,c.c_void_p,*args)(table[index])
    factory=c.c_void_p();result=[]
    try:
        dxgi=c.WinDLL('dxgi')
        create=dxgi.CreateDXGIFactory1
        create.argtypes=[c.POINTER(GUID),c.POINTER(c.c_void_p)];create.restype=c.c_int32
        iid=GUID();iid.data[:]=uuid.UUID('770aae78-f26f-4dba-a829-253c83d1b387').bytes_le
        if create(c.byref(iid),c.byref(factory))<0:return []
        enum=method(factory,12,c.c_int32,c.c_uint32,c.POINTER(c.c_void_p))
        for index in range(64):
            adapter=c.c_void_p()
            if enum(factory,index,c.byref(adapter))<0:break
            try:
                desc=Description()
                if method(adapter,10,c.c_int32,c.POINTER(Description))(adapter,c.byref(desc))<0 or desc.flags&2:continue
                result.append(dict(name=desc.name,vendor={0x10de:'NVIDIA',0x1002:'AMD',0x8086:'Intel'}.get(desc.vendor,'unknown'),
                                   vram_bytes=desc.video,shared_bytes=desc.shared,free_bytes=None,
                                   dedicated=bool(desc.video),load=None,temp=None))
            finally:method(adapter,2,c.c_uint32)(adapter)
    except (OSError,AttributeError):pass
    finally:
        if factory.value:method(factory,2,c.c_uint32)(factory)
    return result
