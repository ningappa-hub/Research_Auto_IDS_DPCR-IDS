//
// Generated file, do not edit! Created by opp_msgtool 6.3 from msg/EthFrameMsg.msg.
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
#include "EthFrameMsg_m.h"

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

Register_Class(EthFrameMsg)

EthFrameMsg::EthFrameMsg(const char *name, short kind) : ::omnetpp::cMessage(name, kind)
{
}

EthFrameMsg::EthFrameMsg(const EthFrameMsg& other) : ::omnetpp::cMessage(other)
{
    copy(other);
}

EthFrameMsg::~EthFrameMsg()
{
    delete [] this->payload;
}

EthFrameMsg& EthFrameMsg::operator=(const EthFrameMsg& other)
{
    if (this == &other) return *this;
    ::omnetpp::cMessage::operator=(other);
    copy(other);
    return *this;
}

void EthFrameMsg::copy(const EthFrameMsg& other)
{
    delete [] this->payload;
    this->payload = (other.payload_arraysize==0) ? nullptr : new int[other.payload_arraysize];
    payload_arraysize = other.payload_arraysize;
    for (size_t i = 0; i < payload_arraysize; i++) {
        this->payload[i] = other.payload[i];
    }
    this->payloadLength = other.payloadLength;
    this->srcAddress = other.srcAddress;
    this->dstAddress = other.dstAddress;
    this->label = other.label;
    this->attackType = other.attackType;
    this->protocol = other.protocol;
}

void EthFrameMsg::parsimPack(omnetpp::cCommBuffer *b) const
{
    ::omnetpp::cMessage::parsimPack(b);
    b->pack(payload_arraysize);
    doParsimArrayPacking(b,this->payload,payload_arraysize);
    doParsimPacking(b,this->payloadLength);
    doParsimPacking(b,this->srcAddress);
    doParsimPacking(b,this->dstAddress);
    doParsimPacking(b,this->label);
    doParsimPacking(b,this->attackType);
    doParsimPacking(b,this->protocol);
}

void EthFrameMsg::parsimUnpack(omnetpp::cCommBuffer *b)
{
    ::omnetpp::cMessage::parsimUnpack(b);
    delete [] this->payload;
    b->unpack(payload_arraysize);
    if (payload_arraysize == 0) {
        this->payload = nullptr;
    } else {
        this->payload = new int[payload_arraysize];
        doParsimArrayUnpacking(b,this->payload,payload_arraysize);
    }
    doParsimUnpacking(b,this->payloadLength);
    doParsimUnpacking(b,this->srcAddress);
    doParsimUnpacking(b,this->dstAddress);
    doParsimUnpacking(b,this->label);
    doParsimUnpacking(b,this->attackType);
    doParsimUnpacking(b,this->protocol);
}

size_t EthFrameMsg::getPayloadArraySize() const
{
    return payload_arraysize;
}

int EthFrameMsg::getPayload(size_t k) const
{
    if (k >= payload_arraysize) throw omnetpp::cRuntimeError("Array of size %lu indexed by %lu", (unsigned long)payload_arraysize, (unsigned long)k);
    return this->payload[k];
}

void EthFrameMsg::setPayloadArraySize(size_t newSize)
{
    int *payload2 = (newSize==0) ? nullptr : new int[newSize];
    size_t minSize = payload_arraysize < newSize ? payload_arraysize : newSize;
    for (size_t i = 0; i < minSize; i++)
        payload2[i] = this->payload[i];
    for (size_t i = minSize; i < newSize; i++)
        payload2[i] = 0;
    delete [] this->payload;
    this->payload = payload2;
    payload_arraysize = newSize;
}

void EthFrameMsg::setPayload(size_t k, int payload)
{
    if (k >= payload_arraysize) throw omnetpp::cRuntimeError("Array of size %lu indexed by %lu", (unsigned long)payload_arraysize, (unsigned long)k);
    this->payload[k] = payload;
}

void EthFrameMsg::insertPayload(size_t k, int payload)
{
    if (k > payload_arraysize) throw omnetpp::cRuntimeError("Array of size %lu indexed by %lu", (unsigned long)payload_arraysize, (unsigned long)k);
    size_t newSize = payload_arraysize + 1;
    int *payload2 = new int[newSize];
    size_t i;
    for (i = 0; i < k; i++)
        payload2[i] = this->payload[i];
    payload2[k] = payload;
    for (i = k + 1; i < newSize; i++)
        payload2[i] = this->payload[i-1];
    delete [] this->payload;
    this->payload = payload2;
    payload_arraysize = newSize;
}

void EthFrameMsg::appendPayload(int payload)
{
    insertPayload(payload_arraysize, payload);
}

void EthFrameMsg::erasePayload(size_t k)
{
    if (k >= payload_arraysize) throw omnetpp::cRuntimeError("Array of size %lu indexed by %lu", (unsigned long)payload_arraysize, (unsigned long)k);
    size_t newSize = payload_arraysize - 1;
    int *payload2 = (newSize == 0) ? nullptr : new int[newSize];
    size_t i;
    for (i = 0; i < k; i++)
        payload2[i] = this->payload[i];
    for (i = k; i < newSize; i++)
        payload2[i] = this->payload[i+1];
    delete [] this->payload;
    this->payload = payload2;
    payload_arraysize = newSize;
}

int EthFrameMsg::getPayloadLength() const
{
    return this->payloadLength;
}

void EthFrameMsg::setPayloadLength(int payloadLength)
{
    this->payloadLength = payloadLength;
}

const char * EthFrameMsg::getSrcAddress() const
{
    return this->srcAddress.c_str();
}

void EthFrameMsg::setSrcAddress(const char * srcAddress)
{
    this->srcAddress = srcAddress;
}

const char * EthFrameMsg::getDstAddress() const
{
    return this->dstAddress.c_str();
}

void EthFrameMsg::setDstAddress(const char * dstAddress)
{
    this->dstAddress = dstAddress;
}

int EthFrameMsg::getLabel() const
{
    return this->label;
}

void EthFrameMsg::setLabel(int label)
{
    this->label = label;
}

const char * EthFrameMsg::getAttackType() const
{
    return this->attackType.c_str();
}

void EthFrameMsg::setAttackType(const char * attackType)
{
    this->attackType = attackType;
}

const char * EthFrameMsg::getProtocol() const
{
    return this->protocol.c_str();
}

void EthFrameMsg::setProtocol(const char * protocol)
{
    this->protocol = protocol;
}

class EthFrameMsgDescriptor : public omnetpp::cClassDescriptor
{
  private:
    mutable const char **propertyNames;
    enum FieldConstants {
        FIELD_payload,
        FIELD_payloadLength,
        FIELD_srcAddress,
        FIELD_dstAddress,
        FIELD_label,
        FIELD_attackType,
        FIELD_protocol,
    };
  public:
    EthFrameMsgDescriptor();
    virtual ~EthFrameMsgDescriptor();

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

Register_ClassDescriptor(EthFrameMsgDescriptor)

EthFrameMsgDescriptor::EthFrameMsgDescriptor() : omnetpp::cClassDescriptor(omnetpp::opp_typename(typeid(dpcrids::EthFrameMsg)), "omnetpp::cMessage")
{
    propertyNames = nullptr;
}

EthFrameMsgDescriptor::~EthFrameMsgDescriptor()
{
    delete[] propertyNames;
}

bool EthFrameMsgDescriptor::doesSupport(omnetpp::cObject *obj) const
{
    return dynamic_cast<EthFrameMsg *>(obj)!=nullptr;
}

const char **EthFrameMsgDescriptor::getPropertyNames() const
{
    if (!propertyNames) {
        static const char *names[] = {  nullptr };
        omnetpp::cClassDescriptor *base = getBaseClassDescriptor();
        const char **baseNames = base ? base->getPropertyNames() : nullptr;
        propertyNames = mergeLists(baseNames, names);
    }
    return propertyNames;
}

const char *EthFrameMsgDescriptor::getProperty(const char *propertyName) const
{
    omnetpp::cClassDescriptor *base = getBaseClassDescriptor();
    return base ? base->getProperty(propertyName) : nullptr;
}

int EthFrameMsgDescriptor::getFieldCount() const
{
    omnetpp::cClassDescriptor *base = getBaseClassDescriptor();
    return base ? 7+base->getFieldCount() : 7;
}

unsigned int EthFrameMsgDescriptor::getFieldTypeFlags(int field) const
{
    omnetpp::cClassDescriptor *base = getBaseClassDescriptor();
    if (base) {
        if (field < base->getFieldCount())
            return base->getFieldTypeFlags(field);
        field -= base->getFieldCount();
    }
    static unsigned int fieldTypeFlags[] = {
        FD_ISARRAY | FD_ISEDITABLE | FD_ISRESIZABLE,    // FIELD_payload
        FD_ISEDITABLE,    // FIELD_payloadLength
        FD_ISEDITABLE,    // FIELD_srcAddress
        FD_ISEDITABLE,    // FIELD_dstAddress
        FD_ISEDITABLE,    // FIELD_label
        FD_ISEDITABLE,    // FIELD_attackType
        FD_ISEDITABLE,    // FIELD_protocol
    };
    return (field >= 0 && field < 7) ? fieldTypeFlags[field] : 0;
}

const char *EthFrameMsgDescriptor::getFieldName(int field) const
{
    omnetpp::cClassDescriptor *base = getBaseClassDescriptor();
    if (base) {
        if (field < base->getFieldCount())
            return base->getFieldName(field);
        field -= base->getFieldCount();
    }
    static const char *fieldNames[] = {
        "payload",
        "payloadLength",
        "srcAddress",
        "dstAddress",
        "label",
        "attackType",
        "protocol",
    };
    return (field >= 0 && field < 7) ? fieldNames[field] : nullptr;
}

int EthFrameMsgDescriptor::findField(const char *fieldName) const
{
    omnetpp::cClassDescriptor *base = getBaseClassDescriptor();
    int baseIndex = base ? base->getFieldCount() : 0;
    if (strcmp(fieldName, "payload") == 0) return baseIndex + 0;
    if (strcmp(fieldName, "payloadLength") == 0) return baseIndex + 1;
    if (strcmp(fieldName, "srcAddress") == 0) return baseIndex + 2;
    if (strcmp(fieldName, "dstAddress") == 0) return baseIndex + 3;
    if (strcmp(fieldName, "label") == 0) return baseIndex + 4;
    if (strcmp(fieldName, "attackType") == 0) return baseIndex + 5;
    if (strcmp(fieldName, "protocol") == 0) return baseIndex + 6;
    return base ? base->findField(fieldName) : -1;
}

const char *EthFrameMsgDescriptor::getFieldTypeString(int field) const
{
    omnetpp::cClassDescriptor *base = getBaseClassDescriptor();
    if (base) {
        if (field < base->getFieldCount())
            return base->getFieldTypeString(field);
        field -= base->getFieldCount();
    }
    static const char *fieldTypeStrings[] = {
        "int",    // FIELD_payload
        "int",    // FIELD_payloadLength
        "string",    // FIELD_srcAddress
        "string",    // FIELD_dstAddress
        "int",    // FIELD_label
        "string",    // FIELD_attackType
        "string",    // FIELD_protocol
    };
    return (field >= 0 && field < 7) ? fieldTypeStrings[field] : nullptr;
}

const char **EthFrameMsgDescriptor::getFieldPropertyNames(int field) const
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

const char *EthFrameMsgDescriptor::getFieldProperty(int field, const char *propertyName) const
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

int EthFrameMsgDescriptor::getFieldArraySize(omnetpp::any_ptr object, int field) const
{
    omnetpp::cClassDescriptor *base = getBaseClassDescriptor();
    if (base) {
        if (field < base->getFieldCount())
            return base->getFieldArraySize(object, field);
        field -= base->getFieldCount();
    }
    EthFrameMsg *pp = omnetpp::fromAnyPtr<EthFrameMsg>(object); (void)pp;
    switch (field) {
        case FIELD_payload: return pp->getPayloadArraySize();
        default: return 0;
    }
}

void EthFrameMsgDescriptor::setFieldArraySize(omnetpp::any_ptr object, int field, int size) const
{
    omnetpp::cClassDescriptor *base = getBaseClassDescriptor();
    if (base) {
        if (field < base->getFieldCount()){
            base->setFieldArraySize(object, field, size);
            return;
        }
        field -= base->getFieldCount();
    }
    EthFrameMsg *pp = omnetpp::fromAnyPtr<EthFrameMsg>(object); (void)pp;
    switch (field) {
        case FIELD_payload: pp->setPayloadArraySize(size); break;
        default: throw omnetpp::cRuntimeError("Cannot set array size of field %d of class 'EthFrameMsg'", field);
    }
}

const char *EthFrameMsgDescriptor::getFieldDynamicTypeString(omnetpp::any_ptr object, int field, int i) const
{
    omnetpp::cClassDescriptor *base = getBaseClassDescriptor();
    if (base) {
        if (field < base->getFieldCount())
            return base->getFieldDynamicTypeString(object,field,i);
        field -= base->getFieldCount();
    }
    EthFrameMsg *pp = omnetpp::fromAnyPtr<EthFrameMsg>(object); (void)pp;
    switch (field) {
        default: return nullptr;
    }
}

std::string EthFrameMsgDescriptor::getFieldValueAsString(omnetpp::any_ptr object, int field, int i) const
{
    omnetpp::cClassDescriptor *base = getBaseClassDescriptor();
    if (base) {
        if (field < base->getFieldCount())
            return base->getFieldValueAsString(object,field,i);
        field -= base->getFieldCount();
    }
    EthFrameMsg *pp = omnetpp::fromAnyPtr<EthFrameMsg>(object); (void)pp;
    switch (field) {
        case FIELD_payload: return long2string(pp->getPayload(i));
        case FIELD_payloadLength: return long2string(pp->getPayloadLength());
        case FIELD_srcAddress: return oppstring2string(pp->getSrcAddress());
        case FIELD_dstAddress: return oppstring2string(pp->getDstAddress());
        case FIELD_label: return long2string(pp->getLabel());
        case FIELD_attackType: return oppstring2string(pp->getAttackType());
        case FIELD_protocol: return oppstring2string(pp->getProtocol());
        default: return "";
    }
}

void EthFrameMsgDescriptor::setFieldValueAsString(omnetpp::any_ptr object, int field, int i, const char *value) const
{
    omnetpp::cClassDescriptor *base = getBaseClassDescriptor();
    if (base) {
        if (field < base->getFieldCount()){
            base->setFieldValueAsString(object, field, i, value);
            return;
        }
        field -= base->getFieldCount();
    }
    EthFrameMsg *pp = omnetpp::fromAnyPtr<EthFrameMsg>(object); (void)pp;
    switch (field) {
        case FIELD_payload: pp->setPayload(i,string2long(value)); break;
        case FIELD_payloadLength: pp->setPayloadLength(string2long(value)); break;
        case FIELD_srcAddress: pp->setSrcAddress((value)); break;
        case FIELD_dstAddress: pp->setDstAddress((value)); break;
        case FIELD_label: pp->setLabel(string2long(value)); break;
        case FIELD_attackType: pp->setAttackType((value)); break;
        case FIELD_protocol: pp->setProtocol((value)); break;
        default: throw omnetpp::cRuntimeError("Cannot set field %d of class 'EthFrameMsg'", field);
    }
}

omnetpp::cValue EthFrameMsgDescriptor::getFieldValue(omnetpp::any_ptr object, int field, int i) const
{
    omnetpp::cClassDescriptor *base = getBaseClassDescriptor();
    if (base) {
        if (field < base->getFieldCount())
            return base->getFieldValue(object,field,i);
        field -= base->getFieldCount();
    }
    EthFrameMsg *pp = omnetpp::fromAnyPtr<EthFrameMsg>(object); (void)pp;
    switch (field) {
        case FIELD_payload: return pp->getPayload(i);
        case FIELD_payloadLength: return pp->getPayloadLength();
        case FIELD_srcAddress: return pp->getSrcAddress();
        case FIELD_dstAddress: return pp->getDstAddress();
        case FIELD_label: return pp->getLabel();
        case FIELD_attackType: return pp->getAttackType();
        case FIELD_protocol: return pp->getProtocol();
        default: throw omnetpp::cRuntimeError("Cannot return field %d of class 'EthFrameMsg' as cValue -- field index out of range?", field);
    }
}

void EthFrameMsgDescriptor::setFieldValue(omnetpp::any_ptr object, int field, int i, const omnetpp::cValue& value) const
{
    omnetpp::cClassDescriptor *base = getBaseClassDescriptor();
    if (base) {
        if (field < base->getFieldCount()){
            base->setFieldValue(object, field, i, value);
            return;
        }
        field -= base->getFieldCount();
    }
    EthFrameMsg *pp = omnetpp::fromAnyPtr<EthFrameMsg>(object); (void)pp;
    switch (field) {
        case FIELD_payload: pp->setPayload(i,omnetpp::checked_int_cast<int>(value.intValue())); break;
        case FIELD_payloadLength: pp->setPayloadLength(omnetpp::checked_int_cast<int>(value.intValue())); break;
        case FIELD_srcAddress: pp->setSrcAddress(value.stringValue()); break;
        case FIELD_dstAddress: pp->setDstAddress(value.stringValue()); break;
        case FIELD_label: pp->setLabel(omnetpp::checked_int_cast<int>(value.intValue())); break;
        case FIELD_attackType: pp->setAttackType(value.stringValue()); break;
        case FIELD_protocol: pp->setProtocol(value.stringValue()); break;
        default: throw omnetpp::cRuntimeError("Cannot set field %d of class 'EthFrameMsg'", field);
    }
}

const char *EthFrameMsgDescriptor::getFieldStructName(int field) const
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

omnetpp::any_ptr EthFrameMsgDescriptor::getFieldStructValuePointer(omnetpp::any_ptr object, int field, int i) const
{
    omnetpp::cClassDescriptor *base = getBaseClassDescriptor();
    if (base) {
        if (field < base->getFieldCount())
            return base->getFieldStructValuePointer(object, field, i);
        field -= base->getFieldCount();
    }
    EthFrameMsg *pp = omnetpp::fromAnyPtr<EthFrameMsg>(object); (void)pp;
    switch (field) {
        default: return omnetpp::any_ptr(nullptr);
    }
}

void EthFrameMsgDescriptor::setFieldStructValuePointer(omnetpp::any_ptr object, int field, int i, omnetpp::any_ptr ptr) const
{
    omnetpp::cClassDescriptor *base = getBaseClassDescriptor();
    if (base) {
        if (field < base->getFieldCount()){
            base->setFieldStructValuePointer(object, field, i, ptr);
            return;
        }
        field -= base->getFieldCount();
    }
    EthFrameMsg *pp = omnetpp::fromAnyPtr<EthFrameMsg>(object); (void)pp;
    switch (field) {
        default: throw omnetpp::cRuntimeError("Cannot set field %d of class 'EthFrameMsg'", field);
    }
}

}  // namespace dpcrids

namespace omnetpp {

}  // namespace omnetpp

