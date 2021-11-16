# flake8: noqa
# Generated by the protocol buffer compiler.  DO NOT EDIT!
# source: geometry.proto

import sys

_b = sys.version_info[0] < 3 and (lambda x: x) or (lambda x: x.encode("latin1"))
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from google.protobuf import reflection as _reflection
from google.protobuf import symbol_database as _symbol_database

# @@protoc_insertion_point(imports)

_sym_db = _symbol_database.Default()


DESCRIPTOR = _descriptor.FileDescriptor(
    name="geometry.proto",
    package="dgp.proto",
    syntax="proto3",
    serialized_options=None,
    serialized_pb=_b(
        '\n\x0egeometry.proto\x12\tdgp.proto"*\n\x07Vector3\x12\t\n\x01x\x18\x01 \x01(\x01\x12\t\n\x01y\x18\x02 \x01(\x01\x12\t\n\x01z\x18\x03 \x01(\x01"<\n\nQuaternion\x12\n\n\x02qx\x18\x01 \x01(\x01\x12\n\n\x02qy\x18\x02 \x01(\x01\x12\n\n\x02qz\x18\x03 \x01(\x01\x12\n\n\x02qw\x18\x04 \x01(\x01"X\n\x04Pose\x12\'\n\x0btranslation\x18\x01 \x01(\x0b\x32\x12.dgp.proto.Vector3\x12\'\n\x08rotation\x18\x02 \x01(\x0b\x32\x15.dgp.proto.Quaternion"\xce\x01\n\x10\x43\x61meraIntrinsics\x12\n\n\x02\x66x\x18\x01 \x01(\x01\x12\n\n\x02\x66y\x18\x02 \x01(\x01\x12\n\n\x02\x63x\x18\x03 \x01(\x01\x12\n\n\x02\x63y\x18\x04 \x01(\x01\x12\x0c\n\x04skew\x18\x05 \x01(\x01\x12\x0b\n\x03\x66ov\x18\x06 \x01(\x01\x12\n\n\x02k1\x18\x07 \x01(\x01\x12\n\n\x02k2\x18\x08 \x01(\x01\x12\n\n\x02k3\x18\t \x01(\x01\x12\n\n\x02k4\x18\n \x01(\x01\x12\n\n\x02k5\x18\x0b \x01(\x01\x12\n\n\x02k6\x18\x0c \x01(\x01\x12\n\n\x02p1\x18\r \x01(\x01\x12\n\n\x02p2\x18\x0e \x01(\x01\x12\x0f\n\x07\x66isheye\x18\x0f \x01(\rb\x06proto3'
    ),
)


_VECTOR3 = _descriptor.Descriptor(
    name="Vector3",
    full_name="dgp.proto.Vector3",
    filename=None,
    file=DESCRIPTOR,
    containing_type=None,
    fields=[
        _descriptor.FieldDescriptor(
            name="x",
            full_name="dgp.proto.Vector3.x",
            index=0,
            number=1,
            type=1,
            cpp_type=5,
            label=1,
            has_default_value=False,
            default_value=float(0),
            message_type=None,
            enum_type=None,
            containing_type=None,
            is_extension=False,
            extension_scope=None,
            serialized_options=None,
            file=DESCRIPTOR,
        ),
        _descriptor.FieldDescriptor(
            name="y",
            full_name="dgp.proto.Vector3.y",
            index=1,
            number=2,
            type=1,
            cpp_type=5,
            label=1,
            has_default_value=False,
            default_value=float(0),
            message_type=None,
            enum_type=None,
            containing_type=None,
            is_extension=False,
            extension_scope=None,
            serialized_options=None,
            file=DESCRIPTOR,
        ),
        _descriptor.FieldDescriptor(
            name="z",
            full_name="dgp.proto.Vector3.z",
            index=2,
            number=3,
            type=1,
            cpp_type=5,
            label=1,
            has_default_value=False,
            default_value=float(0),
            message_type=None,
            enum_type=None,
            containing_type=None,
            is_extension=False,
            extension_scope=None,
            serialized_options=None,
            file=DESCRIPTOR,
        ),
    ],
    extensions=[],
    nested_types=[],
    enum_types=[],
    serialized_options=None,
    is_extendable=False,
    syntax="proto3",
    extension_ranges=[],
    oneofs=[],
    serialized_start=29,
    serialized_end=71,
)


_QUATERNION = _descriptor.Descriptor(
    name="Quaternion",
    full_name="dgp.proto.Quaternion",
    filename=None,
    file=DESCRIPTOR,
    containing_type=None,
    fields=[
        _descriptor.FieldDescriptor(
            name="qx",
            full_name="dgp.proto.Quaternion.qx",
            index=0,
            number=1,
            type=1,
            cpp_type=5,
            label=1,
            has_default_value=False,
            default_value=float(0),
            message_type=None,
            enum_type=None,
            containing_type=None,
            is_extension=False,
            extension_scope=None,
            serialized_options=None,
            file=DESCRIPTOR,
        ),
        _descriptor.FieldDescriptor(
            name="qy",
            full_name="dgp.proto.Quaternion.qy",
            index=1,
            number=2,
            type=1,
            cpp_type=5,
            label=1,
            has_default_value=False,
            default_value=float(0),
            message_type=None,
            enum_type=None,
            containing_type=None,
            is_extension=False,
            extension_scope=None,
            serialized_options=None,
            file=DESCRIPTOR,
        ),
        _descriptor.FieldDescriptor(
            name="qz",
            full_name="dgp.proto.Quaternion.qz",
            index=2,
            number=3,
            type=1,
            cpp_type=5,
            label=1,
            has_default_value=False,
            default_value=float(0),
            message_type=None,
            enum_type=None,
            containing_type=None,
            is_extension=False,
            extension_scope=None,
            serialized_options=None,
            file=DESCRIPTOR,
        ),
        _descriptor.FieldDescriptor(
            name="qw",
            full_name="dgp.proto.Quaternion.qw",
            index=3,
            number=4,
            type=1,
            cpp_type=5,
            label=1,
            has_default_value=False,
            default_value=float(0),
            message_type=None,
            enum_type=None,
            containing_type=None,
            is_extension=False,
            extension_scope=None,
            serialized_options=None,
            file=DESCRIPTOR,
        ),
    ],
    extensions=[],
    nested_types=[],
    enum_types=[],
    serialized_options=None,
    is_extendable=False,
    syntax="proto3",
    extension_ranges=[],
    oneofs=[],
    serialized_start=73,
    serialized_end=133,
)


_POSE = _descriptor.Descriptor(
    name="Pose",
    full_name="dgp.proto.Pose",
    filename=None,
    file=DESCRIPTOR,
    containing_type=None,
    fields=[
        _descriptor.FieldDescriptor(
            name="translation",
            full_name="dgp.proto.Pose.translation",
            index=0,
            number=1,
            type=11,
            cpp_type=10,
            label=1,
            has_default_value=False,
            default_value=None,
            message_type=None,
            enum_type=None,
            containing_type=None,
            is_extension=False,
            extension_scope=None,
            serialized_options=None,
            file=DESCRIPTOR,
        ),
        _descriptor.FieldDescriptor(
            name="rotation",
            full_name="dgp.proto.Pose.rotation",
            index=1,
            number=2,
            type=11,
            cpp_type=10,
            label=1,
            has_default_value=False,
            default_value=None,
            message_type=None,
            enum_type=None,
            containing_type=None,
            is_extension=False,
            extension_scope=None,
            serialized_options=None,
            file=DESCRIPTOR,
        ),
    ],
    extensions=[],
    nested_types=[],
    enum_types=[],
    serialized_options=None,
    is_extendable=False,
    syntax="proto3",
    extension_ranges=[],
    oneofs=[],
    serialized_start=135,
    serialized_end=223,
)


_CAMERAINTRINSICS = _descriptor.Descriptor(
    name="CameraIntrinsics",
    full_name="dgp.proto.CameraIntrinsics",
    filename=None,
    file=DESCRIPTOR,
    containing_type=None,
    fields=[
        _descriptor.FieldDescriptor(
            name="fx",
            full_name="dgp.proto.CameraIntrinsics.fx",
            index=0,
            number=1,
            type=1,
            cpp_type=5,
            label=1,
            has_default_value=False,
            default_value=float(0),
            message_type=None,
            enum_type=None,
            containing_type=None,
            is_extension=False,
            extension_scope=None,
            serialized_options=None,
            file=DESCRIPTOR,
        ),
        _descriptor.FieldDescriptor(
            name="fy",
            full_name="dgp.proto.CameraIntrinsics.fy",
            index=1,
            number=2,
            type=1,
            cpp_type=5,
            label=1,
            has_default_value=False,
            default_value=float(0),
            message_type=None,
            enum_type=None,
            containing_type=None,
            is_extension=False,
            extension_scope=None,
            serialized_options=None,
            file=DESCRIPTOR,
        ),
        _descriptor.FieldDescriptor(
            name="cx",
            full_name="dgp.proto.CameraIntrinsics.cx",
            index=2,
            number=3,
            type=1,
            cpp_type=5,
            label=1,
            has_default_value=False,
            default_value=float(0),
            message_type=None,
            enum_type=None,
            containing_type=None,
            is_extension=False,
            extension_scope=None,
            serialized_options=None,
            file=DESCRIPTOR,
        ),
        _descriptor.FieldDescriptor(
            name="cy",
            full_name="dgp.proto.CameraIntrinsics.cy",
            index=3,
            number=4,
            type=1,
            cpp_type=5,
            label=1,
            has_default_value=False,
            default_value=float(0),
            message_type=None,
            enum_type=None,
            containing_type=None,
            is_extension=False,
            extension_scope=None,
            serialized_options=None,
            file=DESCRIPTOR,
        ),
        _descriptor.FieldDescriptor(
            name="skew",
            full_name="dgp.proto.CameraIntrinsics.skew",
            index=4,
            number=5,
            type=1,
            cpp_type=5,
            label=1,
            has_default_value=False,
            default_value=float(0),
            message_type=None,
            enum_type=None,
            containing_type=None,
            is_extension=False,
            extension_scope=None,
            serialized_options=None,
            file=DESCRIPTOR,
        ),
        _descriptor.FieldDescriptor(
            name="fov",
            full_name="dgp.proto.CameraIntrinsics.fov",
            index=5,
            number=6,
            type=1,
            cpp_type=5,
            label=1,
            has_default_value=False,
            default_value=float(0),
            message_type=None,
            enum_type=None,
            containing_type=None,
            is_extension=False,
            extension_scope=None,
            serialized_options=None,
            file=DESCRIPTOR,
        ),
        _descriptor.FieldDescriptor(
            name="k1",
            full_name="dgp.proto.CameraIntrinsics.k1",
            index=6,
            number=7,
            type=1,
            cpp_type=5,
            label=1,
            has_default_value=False,
            default_value=float(0),
            message_type=None,
            enum_type=None,
            containing_type=None,
            is_extension=False,
            extension_scope=None,
            serialized_options=None,
            file=DESCRIPTOR,
        ),
        _descriptor.FieldDescriptor(
            name="k2",
            full_name="dgp.proto.CameraIntrinsics.k2",
            index=7,
            number=8,
            type=1,
            cpp_type=5,
            label=1,
            has_default_value=False,
            default_value=float(0),
            message_type=None,
            enum_type=None,
            containing_type=None,
            is_extension=False,
            extension_scope=None,
            serialized_options=None,
            file=DESCRIPTOR,
        ),
        _descriptor.FieldDescriptor(
            name="k3",
            full_name="dgp.proto.CameraIntrinsics.k3",
            index=8,
            number=9,
            type=1,
            cpp_type=5,
            label=1,
            has_default_value=False,
            default_value=float(0),
            message_type=None,
            enum_type=None,
            containing_type=None,
            is_extension=False,
            extension_scope=None,
            serialized_options=None,
            file=DESCRIPTOR,
        ),
        _descriptor.FieldDescriptor(
            name="k4",
            full_name="dgp.proto.CameraIntrinsics.k4",
            index=9,
            number=10,
            type=1,
            cpp_type=5,
            label=1,
            has_default_value=False,
            default_value=float(0),
            message_type=None,
            enum_type=None,
            containing_type=None,
            is_extension=False,
            extension_scope=None,
            serialized_options=None,
            file=DESCRIPTOR,
        ),
        _descriptor.FieldDescriptor(
            name="k5",
            full_name="dgp.proto.CameraIntrinsics.k5",
            index=10,
            number=11,
            type=1,
            cpp_type=5,
            label=1,
            has_default_value=False,
            default_value=float(0),
            message_type=None,
            enum_type=None,
            containing_type=None,
            is_extension=False,
            extension_scope=None,
            serialized_options=None,
            file=DESCRIPTOR,
        ),
        _descriptor.FieldDescriptor(
            name="k6",
            full_name="dgp.proto.CameraIntrinsics.k6",
            index=11,
            number=12,
            type=1,
            cpp_type=5,
            label=1,
            has_default_value=False,
            default_value=float(0),
            message_type=None,
            enum_type=None,
            containing_type=None,
            is_extension=False,
            extension_scope=None,
            serialized_options=None,
            file=DESCRIPTOR,
        ),
        _descriptor.FieldDescriptor(
            name="p1",
            full_name="dgp.proto.CameraIntrinsics.p1",
            index=12,
            number=13,
            type=1,
            cpp_type=5,
            label=1,
            has_default_value=False,
            default_value=float(0),
            message_type=None,
            enum_type=None,
            containing_type=None,
            is_extension=False,
            extension_scope=None,
            serialized_options=None,
            file=DESCRIPTOR,
        ),
        _descriptor.FieldDescriptor(
            name="p2",
            full_name="dgp.proto.CameraIntrinsics.p2",
            index=13,
            number=14,
            type=1,
            cpp_type=5,
            label=1,
            has_default_value=False,
            default_value=float(0),
            message_type=None,
            enum_type=None,
            containing_type=None,
            is_extension=False,
            extension_scope=None,
            serialized_options=None,
            file=DESCRIPTOR,
        ),
        _descriptor.FieldDescriptor(
            name="fisheye",
            full_name="dgp.proto.CameraIntrinsics.fisheye",
            index=14,
            number=15,
            type=13,
            cpp_type=3,
            label=1,
            has_default_value=False,
            default_value=0,
            message_type=None,
            enum_type=None,
            containing_type=None,
            is_extension=False,
            extension_scope=None,
            serialized_options=None,
            file=DESCRIPTOR,
        ),
    ],
    extensions=[],
    nested_types=[],
    enum_types=[],
    serialized_options=None,
    is_extendable=False,
    syntax="proto3",
    extension_ranges=[],
    oneofs=[],
    serialized_start=226,
    serialized_end=432,
)

_POSE.fields_by_name["translation"].message_type = _VECTOR3
_POSE.fields_by_name["rotation"].message_type = _QUATERNION
DESCRIPTOR.message_types_by_name["Vector3"] = _VECTOR3
DESCRIPTOR.message_types_by_name["Quaternion"] = _QUATERNION
DESCRIPTOR.message_types_by_name["Pose"] = _POSE
DESCRIPTOR.message_types_by_name["CameraIntrinsics"] = _CAMERAINTRINSICS
_sym_db.RegisterFileDescriptor(DESCRIPTOR)

Vector3 = _reflection.GeneratedProtocolMessageType(
    "Vector3",
    (_message.Message,),
    dict(
        DESCRIPTOR=_VECTOR3,
        __module__="geometry_pb2"
        # @@protoc_insertion_point(class_scope:dgp.proto.Vector3)
    ),
)
_sym_db.RegisterMessage(Vector3)

Quaternion = _reflection.GeneratedProtocolMessageType(
    "Quaternion",
    (_message.Message,),
    dict(
        DESCRIPTOR=_QUATERNION,
        __module__="geometry_pb2"
        # @@protoc_insertion_point(class_scope:dgp.proto.Quaternion)
    ),
)
_sym_db.RegisterMessage(Quaternion)

Pose = _reflection.GeneratedProtocolMessageType(
    "Pose",
    (_message.Message,),
    dict(
        DESCRIPTOR=_POSE,
        __module__="geometry_pb2"
        # @@protoc_insertion_point(class_scope:dgp.proto.Pose)
    ),
)
_sym_db.RegisterMessage(Pose)

CameraIntrinsics = _reflection.GeneratedProtocolMessageType(
    "CameraIntrinsics",
    (_message.Message,),
    dict(
        DESCRIPTOR=_CAMERAINTRINSICS,
        __module__="geometry_pb2"
        # @@protoc_insertion_point(class_scope:dgp.proto.CameraIntrinsics)
    ),
)
_sym_db.RegisterMessage(CameraIntrinsics)


# @@protoc_insertion_point(module_scope)
