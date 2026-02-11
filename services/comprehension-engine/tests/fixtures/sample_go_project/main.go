package main

import (
    "net/http"
)

func main() {
    http.HandleFunc("/health", Health)
    _ = http.ListenAndServe(":8080", nil)
}
