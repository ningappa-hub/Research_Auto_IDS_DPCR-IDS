//
// Generated file, do not edit! Created by opp_msgtool 6.3 from msg/CanFrameMsg.msg.
//

// Disable warnings about unused variables, empty switch stmts, etc:
#ifdef _MSC_VER
#  pragma warning(disable:4101)
#  pragma warning(disable:4065)
#endif

#if defined(__clang__)
#  pragma clang diagnostic ignored "-Wshadow"
#  pragma clang diagnostic ignored "-Wconversion"
#  pragma clang diagnostic ignored "-Wunused-parameter"
#  pragma clang diagnostic ignored "-Wc++98-compat"
#  pragma clang diagnostic ignored "-Wunreachable-code-break"
#  pragma clang diagnostic ignored "-Wold-style-cast"
#elif defined(__GNUC__)
#  pragma GCC diagnostic ignored "-Wshadow"
#  pragma GCC diagnostic ignored "-Wconversion"
#  pragma GCC diagnostic ignored "-Wunused-parameter"
#  pragma GCC diagnostic ignored "-Wold-style-cast"
#  pragma GCC diagnostic ignored "-Wsuggest-attribute=noreturn"
#  pragma GCC diagnostic ignored "-Wfloat-conversion"
#endif

#include <iostream>
#include <sstream>
#include <memory>
#include <type_traits>
#include "CanFrameMsg_m.h"

namespace omnetpp {

// Template pack/unpack rules. They are declared *after* a1l type-specific pack functions for multiple reasons.
// They are in the omnetpp namespace, to allow them to be found by argument-dependent lookup via the cCommBuffer argument

// Packing/unpacking an std::vector
template<typename T, typename A>
void doParsimPacking(omnetpp::cCommBuffer *buffer, const std::vector<T,A>& v)
{
    int n = v.size();
    doParsimPacking(buffer, n);
    for (int i = 0; i < n; i++)
        doParsimPacking(buffer, v[i]);
}

template<typename T, typename A>
void doParsimUnpacking(omnetpp::cCommBuffer *buffer, std::vector<T,A>& v)
{
    int n;
    doParsimUnpacking(buffer, n);
    v.resize(n);
    for (int i = 0; i < n; i++)
        doParsimUnpacking(buffer, v[i]);
}

// Packing/unpacking an std::list
template<typename T, typename A>
void doParsimPacking(omnetpp::cCommBuffer *buffer, const std::list<T,A>& l)
{
    doParsimPacking(buffer, (int)l.size());
    for (typename std::list<T,A>::const_iterator it = l.begin(); it != l.end(); ++it)
        doParsimPacking(buffer, (T&)*it);
}

template<typename T, typename A>
void doParsimUnpacking(omnetpp::cCommBuffer *buffer, std::list<T,A>& l)
{
    int n;
    doParsimUnpacking(buffer, n);
    for (int i = 0; i < n; i++) {
        l.push_back(T());
        doParsimUnpacking(buffer, l.back());
    }
}

// Packing/unpacking an std::set
template<typename T, typename Tr, typename A>
void doParsimPacking(omnetpp::cCommBuffer *buffer, const std::set<T,Tr,A>& s)
{
    doParsimPacking(buffer, (int)s.size());
    for (typename std::set<T,Tr,A>::const_iterator it = s.begin(); it != s.end(); ++it)
        doParsimPacking(buffer, *it);
}

template<typename T, typename Tr, typename A>
void doParsimUnpacking(omnetpp::cCommBuffer *buffer, std::set<T,Tr,A>& s)
{
    int n;
    doParsimUnpacking(buffer, n);
    for (int i = 0; i < n; i++) {
        T x;
        doParsimUnpacking(buffer, x);
        s.insert(x);
    }
}

// Packing/unpacking an std::map
template<typename K, typename V, typename Tr, typename A>
void doParsimPacking(omnetpp::cCommBuffer *buffer, const std::map<K,V,Tr,A>& m)
{
    doParsimPacking(buffer, (int)m.size());
    for (typename std::map<K,V,Tr,A>::const_iterator it = m.begin(); it != m.end(); ++it) {
        doParsimPacking(buffer, it->first);
        doParsimPacking(buffer, it->second);
    }
}

template<typename K, typename V, typename Tr, typename A>
void doParsimUnpacking(omnetpp::cCommBuffer *buffer, std::map<K,V,Tr,A>& m)
{
    int n;
    doParsimUnpacking(buffer, n);
    for (int i = 0; i < n; i++) {
        K k; V v;
        doParsimUnpacking(buffer, k);
        doParsimUnpacking(buffer, v);
        m[k] = v;
    }
}

// Default pack/unpack function for arrays
template<typename T>
void doParsimArrayPacking(omnetpp::cCommBuffer *b, const T *t, int n)
{
    for (int i = 0; i < n; i++)
        doParsimPacking(b, t[i]);
}

template<typename T>
void doParsimArrayUnpacking(omnetpp::cCommBuffer *b, T *t, int n)
{
    for (int i = 0; i < n; i++)
        doParsimUnpacking(b, t[i]);
}

// Default rule to prevent compiler from choosing base class' doParsimPacking() function
template<typename T>
void doParsimPacking(omnetpp::cCommBuffer *, const T& t)
{
    throw omnetpp::cRuntimeError("Parsim error: No doParsimPacking() function for type %s", omnetpp::opp_typename(typeid(t)));
}

template<typename T>
void doParsimUnpacking(omnetpp::cCommBuffer *, T& t)
{
    throw omnetpp::cRuntimeError("Parsim error: No doParsimUnpacking() function for type %s", omnetpp::opp_typename(typeid(t)));
}

}  // namespace omnetpp

namespace dpcrids {

Register_Class(CanFrameMsg)

CanFrameMsg::CanFrameMsg(const char *name, short kind) : ::omnetpp::cMessage(name, kind)
{
}

CanFrameMsg::CanFrameMsg(const CanFrameMsg& other) : ::omnetpp::cMessage(other)
{
    copy(other);
}

CanFrameMsg::~CanFrameMsg()
{
}

CanFrameMsg& CanFrameMsg::operator=(const CanFrameMsg& other)
{
    if (this == &other) return *this;
    ::omnetpp::cMessage::operator=(other);
    copy(other);
    return *this;
}

void CanFrameMsg::copy(const CanFrameMsg& other)
{
    this->canId = other.canId;
    this->dlc = other.dlc;
    for (size_t i = 0; i < 8; i++) {
        this->data[i] = other.data[i];
    }
    this->label = other.label;
    this->attackType = other.attackType;
}

void CanFrameMsg::parsimPack(omnetpp::cCommBuffer *b) const
{
    ::omnetpp::cMessage::parsimPack(b);
    doParsimPacking(b,this->canId);
    doParsimPacking(b,this->dlc);
    doParsimArrayPacking(b,this->data,8);
    doParsimPacking(b,this->label);
    doParsimPacking(b,this->attackType);
}

void CanFrameMsg::parsimUnpack(omnetpp::cCommBuffer *b)
{
    ::omnetpp::cMessage::parsimUnpack(b);
    doParsimUnpacking(b,this->canId);
    doParsimUnpacking(b,this->dlc);
    doParsimArrayUnpacking(b,this->data,8);
    doParsimUnpacking(b,this->label);
    doParsimUnpacking(b,this->attackType);
}

int CanFrameMsg::getCanId() const
{
    return this->canId;
}

void CanFrameMsg::setCanId(int canId)
{
    this->canId = canId;
}

int CanFrameMsg::getDlc() const
{
    return this->dlc;
}

void CanFrameMsg::setDlc(int dlc)
{
    this->dlc = dlc;
}

size_t CanFrameMsg::getDataArraySize() const
{
    return 8;
}

int CanFrameMsg::getData(size_t k) const
{
    if (k >= 8) throw omnetpp::cRuntimeError("Array of size %lu indexed by %lu", (unsigned long)8, (unsigned long)k);
    return this->data[k];
}

void CanFrameMsg::setData(size_t k, int data)
{
    if (k >= 8) throw omnetpp::cRuntimeError("Array of size %lu indexed by %lu", (unsigned long)8, (unsigned long)k);
    this->data[k] = data;
}

int CanFrameMsg::getLabel() const
{
    return this->label;
}

void CanFrameMsg::setLabel(int label)
{
    this->label = label;
}

const char * CanFrameMsg::getAttackType() const
{
    return this->attackType.c_str();
}

void CanFrameMsg::setAttackType(const char * attackType)
{
    this->attackType = attackType;
}

class CanFrameMsgDescriptor : public omnetpp::cClassDescriptor
{
  private:
    mutable const char **propertyNames;
    enum FieldConstants {
        FIELD_canId,
        FIELD_dlc,
        FIELD_data,
        FIELD_label,
        FIELD_attackType,
    };
  public:
    CanFrameMsgDescriptor();
    virtual ~CanFrameMsgDescriptor();

    virtual bool doesSupport(omnetpp::cObject *obj) const override;
    virtual const char **getPropertyNames() const override;
    virtual const char *getProperty(const char *propertyName) const override;
    virtual int getFieldCount() const override;
    virtual const char *getFieldName(int field) const override;
    virtual int findField(const char *fieldName) const override;
    virtual unsigned int getFieldTypeFlags(int field) const override;
    virtual const char *getFieldTypeString(int field) const override;
    virtual const char **getFieldPropertyNames(int field) const override;
    virtual const char *getFieldProperty(int field, const char *propertyName) const override;
    virtual int getFieldArraySize(omnetpp::any_ptr object, int field) const override;
    virtual void setFieldArraySize(omnetpp::any_ptr object, int field, int size) const override;

    virtual const char *getFieldDynamicTypeString(omnetpp::any_ptr object, int field, int i) const override;
    virtual std::string getFieldValueAsString(omnetpp::any_ptr object, int field, int i) const override;
    virtual void setFieldValueAsString(omnetpp::any_ptr object, int field, int i, const char *value) const override;
    virtual omnetpp::cValue getFieldValue(omnetpp::any_ptr object, int field, int i) const override;
    virtual void setFieldValue(omnetpp::any_ptr object, int field, int i, const omnetpp::cValue& value) const override;

    virtual const char *getFieldStructName(int field) const override;
    virtual omnetpp::any_ptr getFieldStructValuePointer(omnetpp::any_ptr object, int field, int i) const override;
    virtual void setFieldStructValuePointer(omnetpp::any_ptr object, int field, int i, omnetpp::any_ptr ptr) const override;
};

Register_ClassDescriptor(CanFrameMsgDescriptor)

CanFrameMsgDescriptor::CanFrameMsgDescriptor() : omnetpp::cClassDescriptor(omnetpp::opp_typename(typeid(dpcrids::CanFrameMsg)), "omnetpp::cMessage")
{
    propertyNames = nullptr;
}

CanFrameMsgDescriptor::~CanFrameMsgDescriptor()
{
    delete[] propertyNames;
}

bool CanFrameMsgDescriptor::doesSupport(omnetpp::cObject *obj) const
{
    return dynamic_cast<CanFrameMsg *>(obj)!=nullptr;
}

const char **CanFrameMsgDescriptor::getPropertyNames() const
{
    if (!propertyNames) {
        static const char *names[] = {  nullptr };
        omnetpp::cClassDescriptor *base = getBaseClassDescriptor();
        const char **baseNames = base ? base->getPropertyNames() : nullptr;
        propertyNames = mergeLists(baseNames, names);
    }
    return propertyNames;
}

const char *CanFrameMsgDescriptor::getProperty(const char *propertyName) const
{
    omnetpp::cClassDescriptor *base = getBaseClassDescriptor();
    return base ? base->getProperty(propertyName) : nullptr;
}

int CanFrameMsgDescriptor::getFieldCount() const
{
    omnetpp::cClassDescriptor *base = getBaseClassDescriptor();
    return base ? 5+base->getFieldCount() : 5;
}

unsigned int CanFrameMsgDescriptor::getFieldTypeFlags(int field) const
{
    omnetpp::cClassDescriptor *base = getBaseClassDescriptor();
    if (base) {
        if (field < base->getFieldCount())
            return base->getFieldTypeFlags(field);
        field -= base->getFieldCount();
    }
    static unsigned int fieldTypeFlags[] = {
        FD_ISEDITABLE,    // FIELD_canId
        FD_ISEDITABLE,    // FIELD_dlc
        FD_ISARRAY | FD_ISEDITABLE,    // FIELD_data
        FD_ISEDITABLE,    // FIELD_label
        FD_ISEDITABLE,    // FIELD_attackType
    };
    return (field >= 0 && field < 5) ? fieldTypeFlags[field] : 0;
}

const char *CanFrameMsgDescriptor::getFieldName(int field) const
{
    omnetpp::cClassDescriptor *base = getBaseClassDescriptor();
    if (base) {
        if (field < base->getFieldCount())
            return base->getFieldName(field);
        field -= base->getFieldCount();
    }
    static const char *fieldNames[] = {
        "canId",
        "dlc",
        "data",
        "label",
        "attackType",
    };
    return (field >= 0 && field < 5) ? fieldNames[field] : nullptr;
}

int CanFrameMsgDescriptor::findField(const char *fieldName) const
{
    omnetpp::cClassDescriptor *base = getBaseClassDescriptor();
    int baseIndex = base ? base->getFieldCount() : 0;
    if (strcmp(fieldName, "canId") == 0) return baseIndex + 0;
    if (strcmp(fieldName, "dlc") == 0) return baseIndex + 1;
    if (strcmp(fieldName, "data") == 0) return baseIndex + 2;
    if (strcmp(fieldName, "label") == 0) return baseIndex + 3;
    if (strcmp(fieldName, "attackType") == 0) return baseIndex + 4;
    return base ? base->findField(fieldName) : -1;
}

const char *CanFrameMsgDescriptor::getFieldTypeString(int field) const
{
    omnetpp::cClassDescriptor *base = getBaseClassDescriptor();
    if (base) {
        if (field < base->getFieldCount())
            return base->getFieldTypeString(field);
        field -= base->getFieldCount();
    }
    static const char *fieldTypeStrings[] = {
        "int",    // FIELD_canId
        "int",    // FIELD_dlc
        "int",    // FIELD_data
        "int",    // FIELD_label
        "string",    // FIELD_attackType
    };
    return (field >= 0 && field < 5) ? fieldTypeStrings[field] : nullptr;
}

const char **CanFrameMsgDescriptor::getFieldPropertyNames(int field) const
{
    omnetpp::cClassDescriptor *base = getBaseClassDescriptor();
    if (base) {
        if (field < base->getFieldCount())
            return base->getFieldPropertyNames(field);
        field -= base->getFieldCount();
    }
    switch (field) {
        default: return nullptr;
    }
}

const char *CanFrameMsgDescriptor::getFieldProperty(int field, const char *propertyName) const
{
    omnetpp::cClassDescriptor *base = getBaseClassDescriptor();
    if (base) {
        if (field < base->getFieldCount())
            return base->getFieldProperty(field, propertyName);
        field -= base->getFieldCount();
    }
    switch (field) {
        default: return nullptr;
    }
}

int CanFrameMsgDescriptor::getFieldArraySize(omnetpp::any_ptr object, int field) const
{
    omnetpp::cClassDescriptor *base = getBaseClassDescriptor();
    if (base) {
        if (field < base->getFieldCount())
            return base->getFieldArraySize(object, field);
        field -= base->getFieldCount();
    }
    CanFrameMsg *pp = omnetpp::fromAnyPtr<CanFrameMsg>(object); (void)pp;
    switch (field) {
        case FIELD_data: return 8;
        default: return 0;
    }
}

void CanFrameMsgDescriptor::setFieldArraySize(omnetpp::any_ptr object, int field, int size) const
{
    omnetpp::cClassDescriptor *base = getBaseClassDescriptor();
    if (base) {
        if (field < base->getFieldCount()){
            base->setFieldArraySize(object, field, size);
            return;
        }
        field -= base->getFieldCount();
    }
    CanFrameMsg *pp = omnetpp::fromAnyPtr<CanFrameMsg>(object); (void)pp;
    switch (field) {
        default: throw omnetpp::cRuntimeError("Cannot set array size of field %d of class 'CanFrameMsg'", field);
    }
}

const char *CanFrameMsgDescriptor::getFieldDynamicTypeString(omnetpp::any_ptr object, int field, int i) const
{
    omnetpp::cClassDescriptor *base = getBaseClassDescriptor();
    if (base) {
        if (field < base->getFieldCount())
            return base->getFieldDynamicTypeString(object,field,i);
        field -= base->getFieldCount();
    }
    CanFrameMsg *pp = omnetpp::fromAnyPtr<CanFrameMsg>(object); (void)pp;
    switch (field) {
        default: return nullptr;
    }
}

std::string CanFrameMsgDescriptor::getFieldValueAsString(omnetpp::any_ptr object, int field, int i) const
{
    omnetpp::cClassDescriptor *base = getBaseClassDescriptor();
    if (base) {
        if (field < base->getFieldCount())
            return base->getFieldValueAsString(object,field,i);
        field -= base->getFieldCount();
    }
    CanFrameMsg *pp = omnetpp::fromAnyPtr<CanFrameMsg>(object); (void)pp;
    switch (field) {
        case FIELD_canId: return long2string(pp->getCanId());
        case FIELD_dlc: return long2string(pp->getDlc());
        case FIELD_data: return long2string(pp->getData(i));
        case FIELD_label: return long2string(pp->getLabel());
        case FIELD_attackType: return oppstring2string(pp->getAttackType());
        default: return "";
    }
}

void CanFrameMsgDescriptor::setFieldValueAsString(omnetpp::any_ptr object, int field, int i, const char *value) const
{
    omnetpp::cClassDescriptor *base = getBaseClassDescriptor();
    if (base) {
        if (field < base->getFieldCount()){
            base->setFieldValueAsString(object, field, i, value);
            return;
        }
        field -= base->getFieldCount();
    }
    CanFrameMsg *pp = omnetpp::fromAnyPtr<CanFrameMsg>(object); (void)pp;
    switch (field) {
        case FIELD_canId: pp->setCanId(string2long(value)); break;
        case FIELD_dlc: pp->setDlc(string2long(value)); break;
        case FIELD_data: pp->setData(i,string2long(value)); break;
        case FIELD_label: pp->setLabel(string2long(value)); break;
        case FIELD_attackType: pp->setAttackType((value)); break;
        default: throw omnetpp::cRuntimeError("Cannot set field %d of class 'CanFrameMsg'", field);
    }
}

omnetpp::cValue CanFrameMsgDescriptor::getFieldValue(omnetpp::any_ptr object, int field, int i) const
{
    omnetpp::cClassDescriptor *base = getBaseClassDescriptor();
    if (base) {
        if (field < base->getFieldCount())
            return base->getFieldValue(object,field,i);
        field -= base->getFieldCount();
    }
    CanFrameMsg *pp = omnetpp::fromAnyPtr<CanFrameMsg>(object); (void)pp;
    switch (field) {
        case FIELD_canId: return pp->getCanId();
        case FIELD_dlc: return pp->getDlc();
        case FIELD_data: return pp->getData(i);
        case FIELD_label: return pp->getLabel();
        case FIELD_attackType: return pp->getAttackType();
        default: throw omnetpp::cRuntimeError("Cannot return field %d of class 'CanFrameMsg' as cValue -- field index out of range?", field);
    }
}

void CanFrameMsgDescriptor::setFieldValue(omnetpp::any_ptr object, int field, int i, const omnetpp::cValue& value) const
{
    omnetpp::cClassDescriptor *base = getBaseClassDescriptor();
    if (base) {
        if (field < base->getFieldCount()){
            base->setFieldValue(object, field, i, value);
            return;
        }
        field -= base->getFieldCount();
    }
    CanFrameMsg *pp = omnetpp::fromAnyPtr<CanFrameMsg>(object); (void)pp;
    switch (field) {
        case FIELD_canId: pp->setCanId(omnetpp::checked_int_cast<int>(value.intValue())); break;
        case FIELD_dlc: pp->setDlc(omnetpp::checked_int_cast<int>(value.intValue())); break;
        case FIELD_data: pp->setData(i,omnetpp::checked_int_cast<int>(value.intValue())); break;
        case FIELD_label: pp->setLabel(omnetpp::checked_int_cast<int>(value.intValue())); break;
        case FIELD_attackType: pp->setAttackType(value.stringValue()); break;
        default: throw omnetpp::cRuntimeError("Cannot set field %d of class 'CanFrameMsg'", field);
    }
}

const char *CanFrameMsgDescriptor::getFieldStructName(int field) const
{
    omnetpp::cClassDescriptor *base = getBaseClassDescriptor();
    if (base) {
        if (field < base->getFieldCount())
            return base->getFieldStructName(field);
        field -= base->getFieldCount();
    }
    switch (field) {
        default: return nullptr;
    };
}

omnetpp::any_ptr CanFrameMsgDescriptor::getFieldStructValuePointer(omnetpp::any_ptr object, int field, int i) const
{
    omnetpp::cClassDescriptor *base = getBaseClassDescriptor();
    if (base) {
        if (field < base->getFieldCount())
            return base->getFieldStructValuePointer(object, field, i);
        field -= base->getFieldCount();
    }
    CanFrameMsg *pp = omnetpp::fromAnyPtr<CanFrameMsg>(object); (void)pp;
    switch (field) {
        default: return omnetpp::any_ptr(nullptr);
    }
}

void CanFrameMsgDescriptor::setFieldStructValuePointer(omnetpp::any_ptr object, int field, int i, omnetpp::any_ptr ptr) const
{
    omnetpp::cClassDescriptor *base = getBaseClassDescriptor();
    if (base) {
        if (field < base->getFieldCount()){
            base->setFieldStructValuePointer(object, field, i, ptr);
            return;
        }
        field -= base->getFieldCount();
    }
    CanFrameMsg *pp = omnetpp::fromAnyPtr<CanFrameMsg>(object); (void)pp;
    switch (field) {
        default: throw omnetpp::cRuntimeError("Cannot set field %d of class 'CanFrameMsg'", field);
    }
}

}  // namespace dpcrids

namespace omnetpp {

}  // namespace omnetpp

