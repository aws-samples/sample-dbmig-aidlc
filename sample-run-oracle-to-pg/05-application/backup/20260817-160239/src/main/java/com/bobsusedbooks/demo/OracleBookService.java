package com.bobsusedbooks.demo;

import com.bobsusedbooks.entities.Book;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import javax.sql.DataSource;
import java.math.BigDecimal;
import java.sql.*;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

/**
 * This service class demonstrates Oracle-specific SQL statements embedded in Java code.
 * It's designed to showcase Amazon Q's SQL conversion capabilities using the /transform command.
 * 
 * IMPORTANT: This class contains Oracle-specific SQL syntax that can be transformed
 * to PostgreSQL using Amazon Q's /transform command.
 */
@Service
public class OracleBookService {

    @Autowired
    private DataSource dataSource;
    
    /**
     * Get book recommendations based on purchase history using Oracle-specific SQL
     */
    public List<Book> getBookRecommendations(Long customerId) throws SQLException {
        List<Book> recommendations = new ArrayList<>();
        
        // Oracle-specific SQL with hierarchical query, analytic functions, and Oracle date functions
        String sql = 
            "WITH customer_genres AS (" +
            "  SELECT b.genre_id, COUNT(*) as purchase_count " +
            "  FROM orders o " +
            "  JOIN order_items oi ON o.id = oi.order_id " +
            "  JOIN books b ON oi.book_id = b.id " +
            "  WHERE o.customer_id = ? " +
            "  AND o.order_date > ADD_MONTHS(SYSDATE, -6) " +
            "  GROUP BY b.genre_id " +
            "  ORDER BY purchase_count DESC " +
            "), " +
            "purchased_books AS (" +
            "  SELECT b.id " +
            "  FROM orders o " +
            "  JOIN order_items oi ON o.id = oi.order_id " +
            "  JOIN books b ON oi.book_id = b.id " +
            "  WHERE o.customer_id = ? " +
            "), " +
            "ranked_recommendations AS (" +
            "  SELECT b.*, " +
            "         ROW_NUMBER() OVER (PARTITION BY b.genre_id ORDER BY b.average_rating DESC NULLS LAST) as genre_rank " +
            "  FROM books b " +
            "  JOIN customer_genres cg ON b.genre_id = cg.genre_id " +
            "  WHERE b.id NOT IN (SELECT id FROM purchased_books) " +
            "  AND b.is_available = 1 " +
            "  AND b.quantity > 0 " +
            ") " +
            "SELECT * FROM ranked_recommendations " +
            "WHERE genre_rank <= 3 " +
            "ORDER BY (SELECT purchase_count FROM customer_genres cg WHERE cg.genre_id = ranked_recommendations.genre_id) DESC, " +
            "genre_rank ASC";
        
        try (Connection conn = dataSource.getConnection();
             PreparedStatement stmt = conn.prepareStatement(sql)) {
            
            stmt.setLong(1, customerId);
            stmt.setLong(2, customerId);
            ResultSet rs = stmt.executeQuery();
            
            while (rs.next()) {
                Book book = mapRowToBook(rs);
                recommendations.add(book);
            }
        }
        
        return recommendations;
    }

    
    /**
     * Get customer purchase patterns using Oracle-specific SQL
     */
    public List<Map<String, Object>> getCustomerPurchasePatterns(Long customerId) throws SQLException {
        List<Map<String, Object>> results = new ArrayList<>();
        
        // Oracle-specific SQL with analytic functions, LISTAGG, and Oracle date functions
        String sql = 
            "SELECT " +
            "  c.id as customer_id, " +
            "  c.name as customer_name, " +
            "  COUNT(DISTINCT o.id) as total_orders, " +
            "  SUM(o.total_amount) as total_spent, " +
            "  AVG(o.total_amount) as avg_order_value, " +
            "  MAX(o.order_date) as last_order_date, " +
            "  ROUND(AVG(LEAD(o.order_date) OVER (PARTITION BY o.customer_id ORDER BY o.order_date) - o.order_date)) as avg_days_between_orders, " +
            "  LISTAGG(DISTINCT g.name, ', ') WITHIN GROUP (ORDER BY COUNT(*) DESC) as top_genres, " +
            "  ROUND(MONTHS_BETWEEN(SYSDATE, MIN(o.order_date))) as customer_age_months " +
            "FROM customers c " +
            "JOIN orders o ON c.id = o.customer_id " +
            "JOIN order_items oi ON o.id = oi.order_id " +
            "JOIN books b ON oi.book_id = b.id " +
            "JOIN genres g ON b.genre_id = g.id " +
            "WHERE c.id = ? " +
            "GROUP BY c.id, c.name";
        
        try (Connection conn = dataSource.getConnection();
             PreparedStatement stmt = conn.prepareStatement(sql)) {
            
            stmt.setLong(1, customerId);
            ResultSet rs = stmt.executeQuery();
            
            ResultSetMetaData metaData = rs.getMetaData();
            int columnCount = metaData.getColumnCount();
            
            while (rs.next()) {
                Map<String, Object> row = new HashMap<>();
                for (int i = 1; i <= columnCount; i++) {
                    row.put(metaData.getColumnLabel(i), rs.getObject(i));
                }
                results.add(row);
            }
        }
        
        return results;
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
