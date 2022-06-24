variable "foo" {
  default = "foo"
}

resource "random_password" "foobar" {
  length = 10
  foo    = "bar"
}
