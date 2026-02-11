package omni.policies.deploy

default allow := false

allow if {
  input.environment == "production"
  input.change_approval == true
  input.security_scan_passed == true
}

allow if {
  input.environment != "production"
  input.security_scan_passed == true
}
