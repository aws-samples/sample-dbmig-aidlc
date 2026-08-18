package com.bobsusedbooks.demo;

import com.bobsusedbooks.entities.Book;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Repository;

import javax.sql.DataSource;
import java.math.BigDecimal;
import java.sql.Connection;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.util.ArrayList;
import java.util.List;

/**
 * This class demonstrates embedded Oracle SQL statements in a Java application.
 * It's designed to be a candidate for SQL conversion using Amazon Q's transform feature.
 * 
 * IMPORTANT: This class contains Oracle-specific SQL syntax that can be transformed
 * to PostgreSQL using Amazon Q's /transform command.
 */
@Repository
public class OracleBookRepository {
    
    @Autowired
    private DataSource dataSource;
    
    /**
     * Find books by genre using Oracle SQL
     */
    public List<Book> findBooksByGenre(Long genreId) throws SQLException {
        List<Book> books = new ArrayList<>();
        
        // Oracle-specific SQL with ROWNUM for pagination
        String sql = "SELECT * FROM BOOKS b " +
                     "WHERE b.genre_id = ? " +
                     "AND ROWNUM <= 100 " +
                     "ORDER BY b.name";
        
        try (Connection conn = dataSource.getConnection();
             PreparedStatement stmt = conn.prepareStatement(sql)) {
            
            stmt.setLong(1, genreId);
            ResultSet rs = stmt.executeQuery();
            
            while (rs.next()) {
                Book book = mapRowToBook(rs);
                books.add(book);
            }
        }
        
        return books;
    }
    
    /**
     * Search books by keyword using Oracle SQL
     */
    public List<Book> searchBooks(String keyword) throws SQLException {
        List<Book> books = new ArrayList<>();
        
        // Oracle-specific SQL with UPPER and concatenation operator ||
        String sql = "SELECT * FROM BOOKS b " +
                     "WHERE UPPER(b.name) LIKE UPPER('%' || ? || '%') " +
                     "OR UPPER(b.author) LIKE UPPER('%' || ? || '%')";
        
        try (Connection conn = dataSource.getConnection();
             PreparedStatement stmt = conn.prepareStatement(sql)) {
            
            stmt.setString(1, keyword);
            stmt.setString(2, keyword);
            ResultSet rs = stmt.executeQuery();
            
            while (rs.next()) {
                Book book = mapRowToBook(rs);
                books.add(book);
            }
        }
        
        return books;
    }
    
    /**
     * Get featured books using Oracle SQL
     */
    public List<Book> getFeaturedBooks() throws SQLException {
        List<Book> books = new ArrayList<>();
        
        // Oracle-specific SQL with NVL function
        String sql = "SELECT * FROM BOOKS b " +
                     "WHERE NVL(b.is_featured, 0) = 1 " +
                     "ORDER BY b.name";
        
        try (Connection conn = dataSource.getConnection();
             PreparedStatement stmt = conn.prepareStatement(sql)) {
            
            ResultSet rs = stmt.executeQuery();
            
            while (rs.next()) {
                Book book = mapRowToBook(rs);
                books.add(book);
            }
        }
        
        return books;
    }
    
    /**
     * Get books with low stock using Oracle SQL
     */
    public List<Book> getBooksWithLowStock(int threshold) throws SQLException {
        List<Book> books = new ArrayList<>();
        
        // Oracle-specific SQL with DECODE function
        String sql = "SELECT b.*, " +
                     "DECODE(b.quantity, 0, 'Out of Stock', " +
                     "                  1, 'Last Copy', " +
                     "                  'In Stock') as stock_status " +
                     "FROM BOOKS b " +
                     "WHERE b.quantity < ? " +
                     "ORDER BY b.quantity ASC";
        
        try (Connection conn = dataSource.getConnection();
             PreparedStatement stmt = conn.prepareStatement(sql)) {
            
            stmt.setInt(1, threshold);
            ResultSet rs = stmt.executeQuery();
            
            while (rs.next()) {
                Book book = mapRowToBook(rs);
                books.add(book);
            }
        }
        
        return books;
    }
    
    
    /**
     * Advanced search for books using Oracle SQL
     */
    public List<Book> advancedSearch(
            String keyword, 
            String author, 
            String isbn, 
            Long publisherId, 
            Long conditionId, 
            Long bookTypeId, 
            Long genreId, 
            BigDecimal minPrice, 
            BigDecimal maxPrice) throws SQLException {
        
        List<Book> books = new ArrayList<>();
        
        // Oracle-specific SQL with complex conditions and TO_DATE function
        StringBuilder sql = new StringBuilder();
        sql.append("SELECT * FROM BOOKS b WHERE 1=1 ");
        
        if (keyword != null) {
            sql.append("AND (UPPER(b.name) LIKE UPPER('%' || ? || '%') OR UPPER(b.author) LIKE UPPER('%' || ? || '%')) ");
        }
        
        if (author != null) {
            sql.append("AND UPPER(b.author) LIKE UPPER('%' || ? || '%') ");
        }
        
        if (isbn != null) {
            sql.append("AND b.isbn LIKE '%' || ? || '%' ");
        }
        
        if (publisherId != null) {
            sql.append("AND b.publisher_id = ? ");
        }
        
        if (conditionId != null) {
            sql.append("AND b.condition_id = ? ");
        }
        
        if (bookTypeId != null) {
            sql.append("AND b.book_type_id = ? ");
        }
        
        if (genreId != null) {
            sql.append("AND b.genre_id = ? ");
        }
        
        if (minPrice != null) {
            sql.append("AND b.price >= ? ");
        }
        
        if (maxPrice != null) {
            sql.append("AND b.price <= ? ");
        }
        
        sql.append("AND b.created_date > TO_DATE('2023-01-01', 'YYYY-MM-DD') ");
        sql.append("ORDER BY b.name");
        
        try (Connection conn = dataSource.getConnection();
             PreparedStatement stmt = conn.prepareStatement(sql.toString())) {
            
            int paramIndex = 1;
            
            if (keyword != null) {
                stmt.setString(paramIndex++, keyword);
                stmt.setString(paramIndex++, keyword);
            }
            
            if (author != null) {
                stmt.setString(paramIndex++, author);
            }
            
            if (isbn != null) {
                stmt.setString(paramIndex++, isbn);
            }
            
            if (publisherId != null) {
                stmt.setLong(paramIndex++, publisherId);
            }
            
            if (conditionId != null) {
                stmt.setLong(paramIndex++, conditionId);
            }
            
            if (bookTypeId != null) {
                stmt.setLong(paramIndex++, bookTypeId);
            }
            
            if (genreId != null) {
                stmt.setLong(paramIndex++, genreId);
            }
            
            if (minPrice != null) {
                stmt.setBigDecimal(paramIndex++, minPrice);
            }
            
            if (maxPrice != null) {
                stmt.setBigDecimal(paramIndex++, maxPrice);
            }
            
            ResultSet rs = stmt.executeQuery();
            
            while (rs.next()) {
                Book book = mapRowToBook(rs);
                books.add(book);
            }
        }
        
        return books;
    }
    
    /**
     * Get top selling books using Oracle SQL
     */
    public List<Book> getTopSellingBooks(int limit) throws SQLException {
        List<Book> books = new ArrayList<>();
        
        // Oracle-specific SQL with analytic functions
        String sql = "SELECT b.* FROM (" +
                     "  SELECT b.*, " +
                     "         ROW_NUMBER() OVER (ORDER BY SUM(s.quantity) DESC) as rank " +
                     "  FROM BOOKS b " +
                     "  JOIN SALES s ON b.id = s.book_id " +
                     "  WHERE s.sale_date > ADD_MONTHS(SYSDATE, -12) " +
                     "  GROUP BY b.id, b.name, b.author, b.isbn, b.price, b.quantity, " +
                     "           b.genre_id, b.publisher_id, b.condition_id, b.book_type_id, " +
                     "           b.is_featured, b.is_bestseller, b.is_new_arrival, " +
                     "           b.seller_id, b.is_available, b.created_by " +
                     ") b " +
                     "WHERE rank <= ?";
        
        try (Connection conn = dataSource.getConnection();
             PreparedStatement stmt = conn.prepareStatement(sql)) {
            
            stmt.setInt(1, limit);
            ResultSet rs = stmt.executeQuery();
            
            while (rs.next()) {
                Book book = mapRowToBook(rs);
                books.add(book);
            }
        }
        
        return books;
    }
   
    
    /**
     * Helper method to map a ResultSet row to a Book object
     */
    private Book mapRowToBook(ResultSet rs) throws SQLException {
        // Implementation would map ResultSet to Book entity
        // This is simplified for the example
        Book book = new Book();
        book.setId(rs.getLong("id"));
        book.setTitle(rs.getString("name"));
        book.setAuthor(rs.getString("author"));
        book.setIsbn(rs.getString("isbn"));
        // Note: price and quantity now in Listings table
        
        return book;
    }
}
