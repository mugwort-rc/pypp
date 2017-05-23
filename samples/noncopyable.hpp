class Noncopyable {
private:
    Noncopyable(const Noncopyable &copy);
    Noncopyable &operator =(const Noncopyable &rhs);

};
