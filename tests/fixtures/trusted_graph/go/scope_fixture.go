package main

// WHY: Test fixture for Go receiver method ambiguity and package scope (DEV-041/046)

type User struct {
    ID string
}

type Order struct {
    ID string
}

// NOTE: Receiver on User
func (u *User) GetStatus() string {
    return "active"
}

// Same method name receiver on Order
func (o *Order) GetStatus() string {
    return "pending"
}

// Package-level function with same base name
func GetStatus() string {
    return "system_ok"
}
