package com.bobsusedbooks.repositories;

import com.bobsusedbooks.entities.Book;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.math.BigDecimal;
import java.util.Collection;
import java.util.List;

@Repository
public interface BookRepository extends JpaRepository<Book, Long> {
    
    // Basic queries using Spring Data JPA method naming conventions
    List<Book> findByGenreId(Long genreId);
    
    Page<Book> findByGenreId(Long genreId, Pageable pageable);
    
    @Query("SELECT DISTINCT b FROM Book b JOIN Listing l ON l.book.id = b.id WHERE l.status = 1 AND (LOWER(b.title) LIKE LOWER(CONCAT('%', :keyword, '%')) OR LOWER(b.author) LIKE LOWER(CONCAT('%', :keyword, '%')))")
    List<Book> findByTitleContainingIgnoreCaseOrAuthorContainingIgnoreCase(@Param("keyword") String title, @Param("keyword") String author);
    
    @Query("SELECT DISTINCT b FROM Book b JOIN Listing l ON l.book.id = b.id WHERE l.status = 1 AND (LOWER(b.title) LIKE LOWER(CONCAT('%', :keyword, '%')) OR LOWER(b.author) LIKE LOWER(CONCAT('%', :keyword, '%')))")
    Page<Book> findByTitleContainingIgnoreCaseOrAuthorContainingIgnoreCase(@Param("keyword") String title, @Param("keyword") String author, Pageable pageable);
    
    
    
    
    
    
    // Method needed by SellController
    
    // Inventory report queries using JPQL
    @Query("SELECT COUNT(b) FROM Book b")
    Integer countTotalBooks();
    
    // BigDecimal calculateTotalInventoryValue();
    
    @Query("SELECT b.genre.name, COUNT(b) FROM Book b GROUP BY b.genre.name ORDER BY COUNT(b) DESC")
    List<Object[]> countBooksByGenre();
    
    @Query("SELECT b FROM Book b JOIN Listing l ON b.id = l.bookId WHERE l.status = 1 AND l.quantity <= :threshold AND l.listingType = 'SYSTEM'")
    List<Book> findBooksWithLowStock(@Param("threshold") int threshold);
    
    @Query("SELECT b.genre.name, SUM(l.price * l.quantity) FROM Book b JOIN Listing l ON b.id = l.bookId WHERE l.status = 1 GROUP BY b.genre.name")
    List<Object[]> calculateInventoryValueByGenre();
    
    
    
    // Find books created by specific users (for admin/offers)
    List<Book> findByCreatedByIn(Collection<String> createdBy);
    
    Page<Book> findByCreatedByIn(Collection<String> createdBy, Pageable pageable);
    
    // Find books NOT created by specific users (for customer books)
    List<Book> findByCreatedByNotIn(Collection<String> createdBy);
    
    Page<Book> findByCreatedByNotIn(Collection<String> createdBy, Pageable pageable);
    
    // Advanced search query using native SQL - joins with listings for condition_id filter
       @Query(value = "SELECT DISTINCT b.* FROM books b " +
              "LEFT JOIN listings l ON b.id = l.book_id AND l.status = 1 " +
              "WHERE " +
              "(:keyword IS NULL OR UPPER(b.title) LIKE UPPER('%' || :keyword || '%') OR UPPER(b.author) LIKE UPPER('%' || :keyword || '%')) AND " +
              "(:author IS NULL OR UPPER(b.author) LIKE UPPER('%' || :author || '%')) AND " +
              "(:isbn IS NULL OR b.isbn LIKE '%' || :isbn || '%') AND " +
              "(:publisherId IS NULL OR b.publisher_id = :publisherId) AND " +
              "(:conditionId IS NULL OR l.condition_id = :conditionId) AND " +
              "(:bookTypeId IS NULL OR b.book_type_id = :bookTypeId) AND " +
              "(:genreId IS NULL OR b.genre_id = :genreId) AND (:minPrice IS NULL OR l.price >= :minPrice) AND (:maxPrice IS NULL OR l.price <= :maxPrice) " +
              "ORDER BY b.title ASC",
              countQuery = "SELECT COUNT(DISTINCT b.id) FROM books b " +
              "LEFT JOIN listings l ON b.id = l.book_id AND l.status = 1 " +
              "WHERE " +
              "(:keyword IS NULL OR UPPER(b.title) LIKE UPPER('%' || :keyword || '%') OR UPPER(b.author) LIKE UPPER('%' || :keyword || '%')) AND " +
              "(:author IS NULL OR UPPER(b.author) LIKE UPPER('%' || :author || '%')) AND " +
              "(:isbn IS NULL OR b.isbn LIKE '%' || :isbn || '%') AND " +
              "(:publisherId IS NULL OR b.publisher_id = :publisherId) AND " +
              "(:conditionId IS NULL OR l.condition_id = :conditionId) AND " +
              "(:bookTypeId IS NULL OR b.book_type_id = :bookTypeId) AND " +
              "(:genreId IS NULL OR b.genre_id = :genreId) AND (:minPrice IS NULL OR l.price >= :minPrice) AND (:maxPrice IS NULL OR l.price <= :maxPrice)",
              nativeQuery = true)
    Page<Book> findByAdvancedSearch(
            @Param("keyword") String keyword,
            @Param("author") String author,
            @Param("isbn") String isbn,
            @Param("publisherId") Long publisherId,
            @Param("conditionId") Long conditionId,
            @Param("bookTypeId") Long bookTypeId,
            @Param("genreId") Long genreId, @Param("minPrice") BigDecimal minPrice, @Param("maxPrice") BigDecimal maxPrice,
            Pageable pageable);

    @Query(value = 
            "SELECT b.* FROM BOOKS b " +
            "WHERE CONTAINS(search_text, ?1, 1) > 0 " +
            "ORDER BY SCORE(1) DESC",
            countQuery = "SELECT COUNT(*) FROM BOOKS b WHERE CONTAINS(search_text, ?1) > 0",
            nativeQuery = true)
    List<Book> fullTextSearchBooks(String searchTerms);        
}
