//
// Generated file, do not edit! Created by opp_msgtool 6.3 from msg/ExpertOutput.msg.
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
#include "ExpertOutput_m.h"

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

Register_Class(ExpertOutput)

ExpertOutput::ExpertOutput(const char *name, short kind) : ::omnetpp::cMessage(name, kind)
{
}

ExpertOutput::ExpertOutput(const ExpertOutput& other) : ::omnetpp::cMessage(other)
{
    copy(other);
}

ExpertOutput::~ExpertOutput()
{
}

ExpertOutput& ExpertOutput::operator=(const ExpertOutput& other)
{
    if (this == &other) return *this;
    ::omnetpp::cMessage::operator=(other);
    copy(other);
    return *this;
}

void ExpertOutput::copy(const ExpertOutput& other)
{
    this->protocol = other.protocol;
    this->logit = other.logit;
    this->rawProb = other.rawProb;
    this->calibratedProb = other.calibratedProb;
    for (size_t i = 0; i < 128; i++) {
        this->embedding[i] = other.embedding[i];
    }
    this->timestamp = other.timestamp;
}

void ExpertOutput::parsimPack(omnetpp::cCommBuffer *b) const
{
    ::omnetpp::cMessage::parsimPack(b);
    doParsimPacking(b,this->protocol);
    doParsimPacking(b,this->logit);
    doParsimPacking(b,this->rawProb);
    doParsimPacking(b,this->calibratedProb);
    doParsimArrayPacking(b,this->embedding,128);
    doParsimPacking(b,this->timestamp);
}

void ExpertOutput::parsimUnpack(omnetpp::cCommBuffer *b)
{
    ::omnetpp::cMessage::parsimUnpack(b);
    doParsimUnpacking(b,this->protocol);
    doParsimUnpacking(b,this->logit);
    doParsimUnpacking(b,this->rawProb);
    doParsimUnpacking(b,this->calibratedProb);
    doParsimArrayUnpacking(b,this->embedding,128);
    doParsimUnpacking(b,this->timestamp);
}

const char * ExpertOutput::getProtocol() const
{
    return this->protocol.c_str();
}

void ExpertOutput::setProtocol(const char * protocol)
{
    this->protocol = protocol;
}

double ExpertOutput::getLogit() const
{
    return this->logit;
}

void ExpertOutput::setLogit(double logit)
{
    this->logit = logit;
}

double ExpertOutput::getRawProb() const
{
    return this->rawProb;
}

void ExpertOutput::setRawProb(double rawProb)
{
    this->rawProb = rawProb;
}

double ExpertOutput::getCalibratedProb() const
{
    return this->calibratedProb;
}

void ExpertOutput::setCalibratedProb(double calibratedProb)
{
    this->calibratedProb = calibratedProb;
}

size_t ExpertOutput::getEmbeddingArraySize() const
{
    return 128;
}

double ExpertOutput::getEmbedding(size_t k) const
{
    if (k >= 128) throw omnetpp::cRuntimeError("Array of size %lu indexed by %lu", (unsigned long)128, (unsigned long)k);
    return this->embedding[k];
}

void ExpertOutput::setEmbedding(size_t k, double embedding)
{
    if (k >= 128) throw omnetpp::cRuntimeError("Array of size %lu indexed by %lu", (unsigned long)128, (unsigned long)k);
    this->embedding[k] = embedding;
}

::omnetpp::simtime_t ExpertOutput::getTimestamp() const
{
    return this->timestamp;
}

void ExpertOutput::setTimestamp(::omnetpp::simtime_t timestamp)
{
    this->timestamp = timestamp;
}

class ExpertOutputDescriptor : public omnetpp::cClassDescriptor
{
  private:
    mutable const char **propertyNames;
    enum FieldConstants {
        FIELD_protocol,
        FIELD_logit,
        FIELD_rawProb,
        FIELD_calibratedProb,
        FIELD_embedding,
        FIELD_timestamp,
    };
  public:
    ExpertOutputDescriptor();
    virtual ~ExpertOutputDescriptor();

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

Register_ClassDescriptor(ExpertOutputDescriptor)

ExpertOutputDescriptor::ExpertOutputDescriptor() : omnetpp::cClassDescriptor(omnetpp::opp_typename(typeid(dpcrids::ExpertOutput)), "omnetpp::cMessage")
{
    propertyNames = nullptr;
}

ExpertOutputDescriptor::~ExpertOutputDescriptor()
{
    delete[] propertyNames;
}

bool ExpertOutputDescriptor::doesSupport(omnetpp::cObject *obj) const
{
    return dynamic_cast<ExpertOutput *>(obj)!=nullptr;
}

const char **ExpertOutputDescriptor::getPropertyNames() const
{
    if (!propertyNames) {
        static const char *names[] = {  nullptr };
        omnetpp::cClassDescriptor *base = getBaseClassDescriptor();
        const char **baseNames = base ? base->getPropertyNames() : nullptr;
        propertyNames = mergeLists(baseNames, names);
    }
    return propertyNames;
}

const char *ExpertOutputDescriptor::getProperty(const char *propertyName) const
{
    omnetpp::cClassDescriptor *base = getBaseClassDescriptor();
    return base ? base->getProperty(propertyName) : nullptr;
}

int ExpertOutputDescriptor::getFieldCount() const
{
    omnetpp::cClassDescriptor *base = getBaseClassDescriptor();
    return base ? 6+base->getFieldCount() : 6;
}

unsigned int ExpertOutputDescriptor::getFieldTypeFlags(int field) const
{
    omnetpp::cClassDescriptor *base = getBaseClassDescriptor();
    if (base) {
        if (field < base->getFieldCount())
            return base->getFieldTypeFlags(field);
        field -= base->getFieldCount();
    }
    static unsigned int fieldTypeFlags[] = {
        FD_ISEDITABLE,    // FIELD_protocol
        FD_ISEDITABLE,    // FIELD_logit
        FD_ISEDITABLE,    // FIELD_rawProb
        FD_ISEDITABLE,    // FIELD_calibratedProb
        FD_ISARRAY | FD_ISEDITABLE,    // FIELD_embedding
        FD_ISEDITABLE,    // FIELD_timestamp
    };
    return (field >= 0 && field < 6) ? fieldTypeFlags[field] : 0;
}

const char *ExpertOutputDescriptor::getFieldName(int field) const
{
    omnetpp::cClassDescriptor *base = getBaseClassDescriptor();
    if (base) {
        if (field < base->getFieldCount())
            return base->getFieldName(field);
        field -= base->getFieldCount();
    }
    static const char *fieldNames[] = {
        "protocol",
        "logit",
        "rawProb",
        "calibratedProb",
        "embedding",
        "timestamp",
    };
    return (field >= 0 && field < 6) ? fieldNames[field] : nullptr;
}

int ExpertOutputDescriptor::findField(const char *fieldName) const
{
    omnetpp::cClassDescriptor *base = getBaseClassDescriptor();
    int baseIndex = base ? base->getFieldCount() : 0;
    if (strcmp(fieldName, "protocol") == 0) return baseIndex + 0;
    if (strcmp(fieldName, "logit") == 0) return baseIndex + 1;
    if (strcmp(fieldName, "rawProb") == 0) return baseIndex + 2;
    if (strcmp(fieldName, "calibratedProb") == 0) return baseIndex + 3;
    if (strcmp(fieldName, "embedding") == 0) return baseIndex + 4;
    if (strcmp(fieldName, "timestamp") == 0) return baseIndex + 5;
    return base ? base->findField(fieldName) : -1;
}

const char *ExpertOutputDescriptor::getFieldTypeString(int field) const
{
    omnetpp::cClassDescriptor *base = getBaseClassDescriptor();
    if (base) {
        if (field < base->getFieldCount())
            return base->getFieldTypeString(field);
        field -= base->getFieldCount();
    }
    static const char *fieldTypeStrings[] = {
        "string",    // FIELD_protocol
        "double",    // FIELD_logit
        "double",    // FIELD_rawProb
        "double",    // FIELD_calibratedProb
        "double",    // FIELD_embedding
        "omnetpp::simtime_t",    // FIELD_timestamp
    };
    return (field >= 0 && field < 6) ? fieldTypeStrings[field] : nullptr;
}

const char **ExpertOutputDescriptor::getFieldPropertyNames(int field) const
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

const char *ExpertOutputDescriptor::getFieldProperty(int field, const char *propertyName) const
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

int ExpertOutputDescriptor::getFieldArraySize(omnetpp::any_ptr object, int field) const
{
    omnetpp::cClassDescriptor *base = getBaseClassDescriptor();
    if (base) {
        if (field < base->getFieldCount())
            return base->getFieldArraySize(object, field);
        field -= base->getFieldCount();
    }
    ExpertOutput *pp = omnetpp::fromAnyPtr<ExpertOutput>(object); (void)pp;
    switch (field) {
        case FIELD_embedding: return 128;
        default: return 0;
    }
}

void ExpertOutputDescriptor::setFieldArraySize(omnetpp::any_ptr object, int field, int size) const
{
    omnetpp::cClassDescriptor *base = getBaseClassDescriptor();
    if (base) {
        if (field < base->getFieldCount()){
            base->setFieldArraySize(object, field, size);
            return;
        }
        field -= base->getFieldCount();
    }
    ExpertOutput *pp = omnetpp::fromAnyPtr<ExpertOutput>(object); (void)pp;
    switch (field) {
        default: throw omnetpp::cRuntimeError("Cannot set array size of field %d of class 'ExpertOutput'", field);
    }
}

const char *ExpertOutputDescriptor::getFieldDynamicTypeString(omnetpp::any_ptr object, int field, int i) const
{
    omnetpp::cClassDescriptor *base = getBaseClassDescriptor();
    if (base) {
        if (field < base->getFieldCount())
            return base->getFieldDynamicTypeString(object,field,i);
        field -= base->getFieldCount();
    }
    ExpertOutput *pp = omnetpp::fromAnyPtr<ExpertOutput>(object); (void)pp;
    switch (field) {
        default: return nullptr;
    }
}

std::string ExpertOutputDescriptor::getFieldValueAsString(omnetpp::any_ptr object, int field, int i) const
{
    omnetpp::cClassDescriptor *base = getBaseClassDescriptor();
    if (base) {
        if (field < base->getFieldCount())
            return base->getFieldValueAsString(object,field,i);
        field -= base->getFieldCount();
    }
    ExpertOutput *pp = omnetpp::fromAnyPtr<ExpertOutput>(object); (void)pp;
    switch (field) {
        case FIELD_protocol: return oppstring2string(pp->getProtocol());
        case FIELD_logit: return double2string(pp->getLogit());
        case FIELD_rawProb: return double2string(pp->getRawProb());
        case FIELD_calibratedProb: return double2string(pp->getCalibratedProb());
        case FIELD_embedding: return double2string(pp->getEmbedding(i));
        case FIELD_timestamp: return simtime2string(pp->getTimestamp());
        default: return "";
    }
}

void ExpertOutputDescriptor::setFieldValueAsString(omnetpp::any_ptr object, int field, int i, const char *value) const
{
    omnetpp::cClassDescriptor *base = getBaseClassDescriptor();
    if (base) {
        if (field < base->getFieldCount()){
            base->setFieldValueAsString(object, field, i, value);
            return;
        }
        field -= base->getFieldCount();
    }
    ExpertOutput *pp = omnetpp::fromAnyPtr<ExpertOutput>(object); (void)pp;
    switch (field) {
        case FIELD_protocol: pp->setProtocol((value)); break;
        case FIELD_logit: pp->setLogit(string2double(value)); break;
        case FIELD_rawProb: pp->setRawProb(string2double(value)); break;
        case FIELD_calibratedProb: pp->setCalibratedProb(string2double(value)); break;
        case FIELD_embedding: pp->setEmbedding(i,string2double(value)); break;
        case FIELD_timestamp: pp->setTimestamp(string2simtime(value)); break;
        default: throw omnetpp::cRuntimeError("Cannot set field %d of class 'ExpertOutput'", field);
    }
}

omnetpp::cValue ExpertOutputDescriptor::getFieldValue(omnetpp::any_ptr object, int field, int i) const
{
    omnetpp::cClassDescriptor *base = getBaseClassDescriptor();
    if (base) {
        if (field < base->getFieldCount())
            return base->getFieldValue(object,field,i);
        field -= base->getFieldCount();
    }
    ExpertOutput *pp = omnetpp::fromAnyPtr<ExpertOutput>(object); (void)pp;
    switch (field) {
        case FIELD_protocol: return pp->getProtocol();
        case FIELD_logit: return pp->getLogit();
        case FIELD_rawProb: return pp->getRawProb();
        case FIELD_calibratedProb: return pp->getCalibratedProb();
        case FIELD_embedding: return pp->getEmbedding(i);
        case FIELD_timestamp: return pp->getTimestamp().dbl();
        default: throw omnetpp::cRuntimeError("Cannot return field %d of class 'ExpertOutput' as cValue -- field index out of range?", field);
    }
}

void ExpertOutputDescriptor::setFieldValue(omnetpp::any_ptr object, int field, int i, const omnetpp::cValue& value) const
{
    omnetpp::cClassDescriptor *base = getBaseClassDescriptor();
    if (base) {
        if (field < base->getFieldCount()){
            base->setFieldValue(object, field, i, value);
            return;
        }
        field -= base->getFieldCount();
    }
    ExpertOutput *pp = omnetpp::fromAnyPtr<ExpertOutput>(object); (void)pp;
    switch (field) {
        case FIELD_protocol: pp->setProtocol(value.stringValue()); break;
        case FIELD_logit: pp->setLogit(value.doubleValue()); break;
        case FIELD_rawProb: pp->setRawProb(value.doubleValue()); break;
        case FIELD_calibratedProb: pp->setCalibratedProb(value.doubleValue()); break;
        case FIELD_embedding: pp->setEmbedding(i,value.doubleValue()); break;
        case FIELD_timestamp: pp->setTimestamp(value.doubleValue()); break;
        default: throw omnetpp::cRuntimeError("Cannot set field %d of class 'ExpertOutput'", field);
    }
}

const char *ExpertOutputDescriptor::getFieldStructName(int field) const
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

omnetpp::any_ptr ExpertOutputDescriptor::getFieldStructValuePointer(omnetpp::any_ptr object, int field, int i) const
{
    omnetpp::cClassDescriptor *base = getBaseClassDescriptor();
    if (base) {
        if (field < base->getFieldCount())
            return base->getFieldStructValuePointer(object, field, i);
        field -= base->getFieldCount();
    }
    ExpertOutput *pp = omnetpp::fromAnyPtr<ExpertOutput>(object); (void)pp;
    switch (field) {
        default: return omnetpp::any_ptr(nullptr);
    }
}

void ExpertOutputDescriptor::setFieldStructValuePointer(omnetpp::any_ptr object, int field, int i, omnetpp::any_ptr ptr) const
{
    omnetpp::cClassDescriptor *base = getBaseClassDescriptor();
    if (base) {
        if (field < base->getFieldCount()){
            base->setFieldStructValuePointer(object, field, i, ptr);
            return;
        }
        field -= base->getFieldCount();
    }
    ExpertOutput *pp = omnetpp::fromAnyPtr<ExpertOutput>(object); (void)pp;
    switch (field) {
        default: throw omnetpp::cRuntimeError("Cannot set field %d of class 'ExpertOutput'", field);
    }
}

}  // namespace dpcrids

namespace omnetpp {

}  // namespace omnetpp

