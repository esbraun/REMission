import reproduce
reproduce.image='sha256:ce346feace2ae607ebd574e1bb681d594c9b676c06b56f8ba8d50b858a577faa'
reproduce.checks(reproduce.root)
reproduce.checks(reproduce.out/'https-clone')
reproduce.run(['git','status','--porcelain'],reproduce.out/'https-clone')
