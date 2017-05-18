class VirtualMethod {
public:
    virtual ~VirtualMethod()
    {}

    virtual void v(int hoge)
    {}

    virtual int p(int x, int y) const = 0;

};
