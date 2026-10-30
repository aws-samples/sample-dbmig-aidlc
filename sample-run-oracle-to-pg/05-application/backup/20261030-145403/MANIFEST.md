# Backup manifest — 20261030-145403

backup_mode: **full-tree** (the app is not a git repo). The whole in-scope tree (346 files, build output and `.bak` leftovers excluded) was copied here before the first edit. Restore: copy this tree back over the app directory; compare: `diff -ru <this dir> <app dir>`.

Files actually edited (18):

- `pom.xml`
- `src/main/java/com/bobsusedbooks/config/DatabaseInfoConfig.java`
- `src/main/java/com/bobsusedbooks/config/DatabaseInfoController.java`
- `src/main/java/com/bobsusedbooks/demo/OracleBookRepository.java`
- `src/main/java/com/bobsusedbooks/demo/OracleBookService.java`
- `src/main/java/com/bobsusedbooks/entities/Address.java`
- `src/main/java/com/bobsusedbooks/entities/Book.java`
- `src/main/java/com/bobsusedbooks/entities/BookCover.java`
- `src/main/java/com/bobsusedbooks/entities/Customer.java`
- `src/main/java/com/bobsusedbooks/entities/Listing.java`
- `src/main/java/com/bobsusedbooks/entities/Order.java`
- `src/main/java/com/bobsusedbooks/entities/PasswordResetToken.java`
- `src/main/java/com/bobsusedbooks/entities/ShoppingCartItem.java`
- `src/main/java/com/bobsusedbooks/repositories/BookRepository.java`
- `src/main/java/com/bobsusedbooks/repositories/CustomerRepository.java`
- `src/main/java/com/bobsusedbooks/services/BookService.java`
- `src/main/java/com/bobsusedbooks/utils/LoadCoverImages.java`
- `src/main/resources/application.properties`

Note: this tree holds the ORIGINAL `application.properties`, including its plaintext password. Keep it out of version control (the `migrations/` folder is git-ignored).
