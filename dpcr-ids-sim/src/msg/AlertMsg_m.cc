//
// Generated file, do not edit! Created by opp_msgtool 6.3 from msg/AlertMsg.msg.
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
#include "AlertMsg_m.h"

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

Register_Class(AlertMsg)

AlertMsg::AlertMsg(const char *name, short kind) : ::omnetpp::cMessage(name, kind)
{
}

AlertMsg::AlertMsg(const AlertMsg& other) : ::omnetpp::cMessage(other)
{
    copy(other);
}

AlertMsg::~AlertMsg()
{
}

AlertMsg& AlertMsg::operator=(const AlertMsg& other)
{
    if (this == &other) return *this;
    ::omnetpp::cMessage::operator=(other);
    copy(other);
    return *this;
}

void AlertMsg::copy(const AlertMsg& other)
{
    this->decision = other.decision;
    this->path = other.path;
    this->pAttackRaw = other.pAttackRaw;
    this->pAttackCalibrated = other.pAttackCalibrated;
    this->latencyMs = other.latencyMs;
    this->escalateFlag = other.escalateFlag;
    this->timestamp = other.timestamp;
}

void AlertMsg::parsimPack(omnetpp::cCommBuffer *b) const
{
    ::omnetpp::cMessage::parsimPack(b);
    doParsimPacking(b,this->decision);
    doParsimPacking(b,this->path);
    doParsimPacking(b,this->pAttackRaw);
    doParsimPacking(b,this->pAttackCalibrated);
    doParsimPacking(b,this->latencyMs);
    doParsimPacking(b,this->escalateFlag);
    doParsimPacking(b,this->timestamp);
}

void AlertMsg::parsimUnpack(omnetpp::cCommBuffer *b)
{
    ::omnetpp::cMessage::parsimUnpack(b);
    doParsimUnpacking(b,this->decision);
    doParsimUnpacking(b,this->path);
    doParsimUnpacking(b,this->pAttackRaw);
    doParsimUnpacking(b,this->pAttackCalibrated);
    doParsimUnpacking(b,this->latencyMs);
    doParsimUnpacking(b,this->escalateFlag);
    doParsimUnpacking(b,this->timestamp);
}

const char * AlertMsg::getDecision() const
{
    return this->decision.c_str();
}

void AlertMsg::setDecision(const char * decision)
{
    this->decision = decision;
}

const char * AlertMsg::getPath() const
{
    return this->path.c_str();
}

void AlertMsg::setPath(const char * path)
{
    this->path = path;
}

double AlertMsg::getPAttackRaw() const
{
    return this->pAttackRaw;
}

void AlertMsg::setPAttackRaw(double pAttackRaw)
{
    this->pAttackRaw = pAttackRaw;
}

double AlertMsg::getPAttackCalibrated() const
{
    return this->pAttackCalibrated;
}

void AlertMsg::setPAttackCalibrated(double pAttackCalibrated)
{
    this->pAttackCalibrated = pAttackCalibrated;
}

double AlertMsg::getLatencyMs() const
{
    return this->latencyMs;
}

void AlertMsg::setLatencyMs(double latencyMs)
{
    this->latencyMs = latencyMs;
}

bool AlertMsg::getEscalateFlag() const
{
    return this->escalateFlag;
}

void AlertMsg::setEscalateFlag(bool escalateFlag)
{
    this->escalateFlag = escalateFlag;
}

::omnetpp::simtime_t AlertMsg::getTimestamp() const
{
    return this->timestamp;
}

void AlertMsg::setTimestamp(::omnetpp::simtime_t timestamp)
{
    this->timestamp = timestamp;
}

class AlertMsgDescriptor : public omnetpp::cClassDescriptor
{
  private:
    mutable const char **propertyNames;
    enum FieldConstants {
        FIELD_decision,
        FIELD_path,
        FIELD_pAttackRaw,
        FIELD_pAttackCalibrated,
        FIELD_latencyMs,
        FIELD_escalateFlag,
        FIELD_timestamp,
    };
  public:
    AlertMsgDescriptor();
    virtual ~AlertMsgDescriptor();

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

Register_ClassDescriptor(AlertMsgDescriptor)

AlertMsgDescriptor::AlertMsgDescriptor() : omnetpp::cClassDescriptor(omnetpp::opp_typename(typeid(dpcrids::AlertMsg)), "omnetpp::cMessage")
{
    propertyNames = nullptr;
}

AlertMsgDescriptor::~AlertMsgDescriptor()
{
    delete[] propertyNames;
}

bool AlertMsgDescriptor::doesSupport(omnetpp::cObject *obj) const
{
    return dynamic_cast<AlertMsg *>(obj)!=nullptr;
}

const char **AlertMsgDescriptor::getPropertyNames() const
{
    if (!propertyNames) {
        static const char *names[] = {  nullptr };
        omnetpp::cClassDescriptor *base = getBaseClassDescriptor();
        const char **baseNames = base ? base->getPropertyNames() : nullptr;
        propertyNames = mergeLists(baseNames, names);
    }
    return propertyNames;
}

const char *AlertMsgDescriptor::getProperty(const char *propertyName) const
{
    omnetpp::cClassDescriptor *base = getBaseClassDescriptor();
    return base ? base->getProperty(propertyName) : nullptr;
}

int AlertMsgDescriptor::getFieldCount() const
{
    omnetpp::cClassDescriptor *base = getBaseClassDescriptor();
    return base ? 7+base->getFieldCount() : 7;
}

unsigned int AlertMsgDescriptor::getFieldTypeFlags(int field) const
{
    omnetpp::cClassDescriptor *base = getBaseClassDescriptor();
    if (base) {
        if (field < base->getFieldCount())
            return base->getFieldTypeFlags(field);
        field -= base->getFieldCount();
    }
    static unsigned int fieldTypeFlags[] = {
        FD_ISEDITABLE,    // FIELD_decision
        FD_ISEDITABLE,    // FIELD_path
        FD_ISEDITABLE,    // FIELD_pAttackRaw
        FD_ISEDITABLE,    // FIELD_pAttackCalibrated
        FD_ISEDITABLE,    // FIELD_latencyMs
        FD_ISEDITABLE,    // FIELD_escalateFlag
        FD_ISEDITABLE,    // FIELD_timestamp
    };
    return (field >= 0 && field < 7) ? fieldTypeFlags[field] : 0;
}

const char *AlertMsgDescriptor::getFieldName(int field) const
{
    omnetpp::cClassDescriptor *base = getBaseClassDescriptor();
    if (base) {
        if (field < base->getFieldCount())
            return base->getFieldName(field);
        field -= base->getFieldCount();
    }
    static const char *fieldNames[] = {
        "decision",
        "path",
        "pAttackRaw",
        "pAttackCalibrated",
        "latencyMs",
        "escalateFlag",
        "timestamp",
    };
    return (field >= 0 && field < 7) ? fieldNames[field] : nullptr;
}

int AlertMsgDescriptor::findField(const char *fieldName) const
{
    omnetpp::cClassDescriptor *base = getBaseClassDescriptor();
    int baseIndex = base ? base->getFieldCount() : 0;
    if (strcmp(fieldName, "decision") == 0) return baseIndex + 0;
    if (strcmp(fieldName, "path") == 0) return baseIndex + 1;
    if (strcmp(fieldName, "pAttackRaw") == 0) return baseIndex + 2;
    if (strcmp(fieldName, "pAttackCalibrated") == 0) return baseIndex + 3;
    if (strcmp(fieldName, "latencyMs") == 0) return baseIndex + 4;
    if (strcmp(fieldName, "escalateFlag") == 0) return baseIndex + 5;
    if (strcmp(fieldName, "timestamp") == 0) return baseIndex + 6;
    return base ? base->findField(fieldName) : -1;
}

const char *AlertMsgDescriptor::getFieldTypeString(int field) const
{
    omnetpp::cClassDescriptor *base = getBaseClassDescriptor();
    if (base) {
        if (field < base->getFieldCount())
            return base->getFieldTypeString(field);
        field -= base->getFieldCount();
    }
    static const char *fieldTypeStrings[] = {
        "string",    // FIELD_decision
        "string",    // FIELD_path
        "double",    // FIELD_pAttackRaw
        "double",    // FIELD_pAttackCalibrated
        "double",    // FIELD_latencyMs
        "bool",    // FIELD_escalateFlag
        "omnetpp::simtime_t",    // FIELD_timestamp
    };
    return (field >= 0 && field < 7) ? fieldTypeStrings[field] : nullptr;
}

const char **AlertMsgDescriptor::getFieldPropertyNames(int field) const
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

const char *AlertMsgDescriptor::getFieldProperty(int field, const char *propertyName) const
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

int AlertMsgDescriptor::getFieldArraySize(omnetpp::any_ptr object, int field) const
{
    omnetpp::cClassDescriptor *base = getBaseClassDescriptor();
    if (base) {
        if (field < base->getFieldCount())
            return base->getFieldArraySize(object, field);
        field -= base->getFieldCount();
    }
    AlertMsg *pp = omnetpp::fromAnyPtr<AlertMsg>(object); (void)pp;
    switch (field) {
        default: return 0;
    }
}

void AlertMsgDescriptor::setFieldArraySize(omnetpp::any_ptr object, int field, int size) const
{
    omnetpp::cClassDescriptor *base = getBaseClassDescriptor();
    if (base) {
        if (field < base->getFieldCount()){
            base->setFieldArraySize(object, field, size);
            return;
        }
        field -= base->getFieldCount();
    }
    AlertMsg *pp = omnetpp::fromAnyPtr<AlertMsg>(object); (void)pp;
    switch (field) {
        default: throw omnetpp::cRuntimeError("Cannot set array size of field %d of class 'AlertMsg'", field);
    }
}

const char *AlertMsgDescriptor::getFieldDynamicTypeString(omnetpp::any_ptr object, int field, int i) const
{
    omnetpp::cClassDescriptor *base = getBaseClassDescriptor();
    if (base) {
        if (field < base->getFieldCount())
            return base->getFieldDynamicTypeString(object,field,i);
        field -= base->getFieldCount();
    }
    AlertMsg *pp = omnetpp::fromAnyPtr<AlertMsg>(object); (void)pp;
    switch (field) {
        default: return nullptr;
    }
}

std::string AlertMsgDescriptor::getFieldValueAsString(omnetpp::any_ptr object, int field, int i) const
{
    omnetpp::cClassDescriptor *base = getBaseClassDescriptor();
    if (base) {
        if (field < base->getFieldCount())
            return base->getFieldValueAsString(object,field,i);
        field -= base->getFieldCount();
    }
    AlertMsg *pp = omnetpp::fromAnyPtr<AlertMsg>(object); (void)pp;
    switch (field) {
        case FIELD_decision: return oppstring2string(pp->getDecision());
        case FIELD_path: return oppstring2string(pp->getPath());
        case FIELD_pAttackRaw: return double2string(pp->getPAttackRaw());
        case FIELD_pAttackCalibrated: return double2string(pp->getPAttackCalibrated());
        case FIELD_latencyMs: return double2string(pp->getLatencyMs());
        case FIELD_escalateFlag: return bool2string(pp->getEscalateFlag());
        case FIELD_timestamp: return simtime2string(pp->getTimestamp());
        default: return "";
    }
}

void AlertMsgDescriptor::setFieldValueAsString(omnetpp::any_ptr object, int field, int i, const char *value) const
{
    omnetpp::cClassDescriptor *base = getBaseClassDescriptor();
    if (base) {
        if (field < base->getFieldCount()){
            base->setFieldValueAsString(object, field, i, value);
            return;
        }
        field -= base->getFieldCount();
    }
    AlertMsg *pp = omnetpp::fromAnyPtr<AlertMsg>(object); (void)pp;
    switch (field) {
        case FIELD_decision: pp->setDecision((value)); break;
        case FIELD_path: pp->setPath((value)); break;
        case FIELD_pAttackRaw: pp->setPAttackRaw(string2double(value)); break;
        case FIELD_pAttackCalibrated: pp->setPAttackCalibrated(string2double(value)); break;
        case FIELD_latencyMs: pp->setLatencyMs(string2double(value)); break;
        case FIELD_escalateFlag: pp->setEscalateFlag(string2bool(value)); break;
        case FIELD_timestamp: pp->setTimestamp(string2simtime(value)); break;
        default: throw omnetpp::cRuntimeError("Cannot set field %d of class 'AlertMsg'", field);
    }
}

omnetpp::cValue AlertMsgDescriptor::getFieldValue(omnetpp::any_ptr object, int field, int i) const
{
    omnetpp::cClassDescriptor *base = getBaseClassDescriptor();
    if (base) {
        if (field < base->getFieldCount())
            return base->getFieldValue(object,field,i);
        field -= base->getFieldCount();
    }
    AlertMsg *pp = omnetpp::fromAnyPtr<AlertMsg>(object); (void)pp;
    switch (field) {
        case FIELD_decision: return pp->getDecision();
        case FIELD_path: return pp->getPath();
        case FIELD_pAttackRaw: return pp->getPAttackRaw();
        case FIELD_pAttackCalibrated: return pp->getPAttackCalibrated();
        case FIELD_latencyMs: return pp->getLatencyMs();
        case FIELD_escalateFlag: return pp->getEscalateFlag();
        case FIELD_timestamp: return pp->getTimestamp().dbl();
        default: throw omnetpp::cRuntimeError("Cannot return field %d of class 'AlertMsg' as cValue -- field index out of range?", field);
    }
}

void AlertMsgDescriptor::setFieldValue(omnetpp::any_ptr object, int field, int i, const omnetpp::cValue& value) const
{
    omnetpp::cClassDescriptor *base = getBaseClassDescriptor();
    if (base) {
        if (field < base->getFieldCount()){
            base->setFieldValue(object, field, i, value);
            return;
        }
        field -= base->getFieldCount();
    }
    AlertMsg *pp = omnetpp::fromAnyPtr<AlertMsg>(object); (void)pp;
    switch (field) {
        case FIELD_decision: pp->setDecision(value.stringValue()); break;
        case FIELD_path: pp->setPath(value.stringValue()); break;
        case FIELD_pAttackRaw: pp->setPAttackRaw(value.doubleValue()); break;
        case FIELD_pAttackCalibrated: pp->setPAttackCalibrated(value.doubleValue()); break;
        case FIELD_latencyMs: pp->setLatencyMs(value.doubleValue()); break;
        case FIELD_escalateFlag: pp->setEscalateFlag(value.boolValue()); break;
        case FIELD_timestamp: pp->setTimestamp(value.doubleValue()); break;
        default: throw omnetpp::cRuntimeError("Cannot set field %d of class 'AlertMsg'", field);
    }
}

const char *AlertMsgDescriptor::getFieldStructName(int field) const
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

omnetpp::any_ptr AlertMsgDescriptor::getFieldStructValuePointer(omnetpp::any_ptr object, int field, int i) const
{
    omnetpp::cClassDescriptor *base = getBaseClassDescriptor();
    if (base) {
        if (field < base->getFieldCount())
            return base->getFieldStructValuePointer(object, field, i);
        field -= base->getFieldCount();
    }
    AlertMsg *pp = omnetpp::fromAnyPtr<AlertMsg>(object); (void)pp;
    switch (field) {
        default: return omnetpp::any_ptr(nullptr);
    }
}

void AlertMsgDescriptor::setFieldStructValuePointer(omnetpp::any_ptr object, int field, int i, omnetpp::any_ptr ptr) const
{
    omnetpp::cClassDescriptor *base = getBaseClassDescriptor();
    if (base) {
        if (field < base->getFieldCount()){
            base->setFieldStructValuePointer(object, field, i, ptr);
            return;
        }
        field -= base->getFieldCount();
    }
    AlertMsg *pp = omnetpp::fromAnyPtr<AlertMsg>(object); (void)pp;
    switch (field) {
        default: throw omnetpp::cRuntimeError("Cannot set field %d of class 'AlertMsg'", field);
    }
}

}  // namespace dpcrids

namespace omnetpp {

}  // namespace omnetpp

