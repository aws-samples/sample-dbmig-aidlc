# App conversion log

Backup: `05-application/backup/20260928-235158/` (full in-scope tree, taken before the first edit; app not in git).
17 files edited (148 changed lines):

- `pom.xml`, `src/main/resources/application.properties`
- entities: `Address`, `Book`, `BookCover`, `Customer`, `Listing`, `Order`, `PasswordResetToken`, `ShoppingCartItem` (16 `@JdbcTypeCode`, imports added)
- `repositories/BookRepository.java` (full-text), `services/BookService.java` (query builder),
  `repositories/CustomerRepository.java` (flag comment only)
- `config/DatabaseInfoConfig.java`, `config/DatabaseInfoController.java`
- `demo/OracleBookRepository.java`, `demo/OracleBookService.java` (dialect + pre-existing flag)

Restore: `(cd backup/20260928-235158 && find . -type f -exec cp -p {} "<app>/{}" \;)`.
