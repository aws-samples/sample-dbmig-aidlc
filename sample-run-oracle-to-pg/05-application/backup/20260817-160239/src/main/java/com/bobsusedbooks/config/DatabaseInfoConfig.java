package com.bobsusedbooks.config;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Configuration;
import org.springframework.web.servlet.config.annotation.WebMvcConfigurer;
import org.springframework.web.servlet.config.annotation.InterceptorRegistry;
import org.springframework.web.servlet.HandlerInterceptor;
import org.springframework.web.servlet.ModelAndView;

import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;

@Configuration
public class DatabaseInfoConfig implements WebMvcConfigurer {

    @Value("${spring.datasource.url}")
    private String datasourceUrl;

    @Value("${spring.datasource.username}")
    private String datasourceUsername;

    @Override
    public void addInterceptors(InterceptorRegistry registry) {
        registry.addInterceptor(new DatabaseInfoInterceptor(datasourceUrl, datasourceUsername));
    }

    private static class DatabaseInfoInterceptor implements HandlerInterceptor {
        private final String datasourceUrl;
        private final String datasourceUsername;

        public DatabaseInfoInterceptor(String datasourceUrl, String datasourceUsername) {
            this.datasourceUrl = datasourceUrl;
            this.datasourceUsername = datasourceUsername;
        }

        @Override
        public void postHandle(HttpServletRequest request, HttpServletResponse response, 
                              Object handler, ModelAndView modelAndView) {
            if (modelAndView != null) {
                // Extract hostname, port, and database from JDBC URL
                String connectionInfo = extractConnectionInfo(datasourceUrl, datasourceUsername);
                modelAndView.addObject("databaseInfo", connectionInfo);
            }
        }

        private String extractConnectionInfo(String jdbcUrl, String username) {
            try {
                // Format: jdbc:oracle:thin:@//localhost:1521/freepdb1
                String connectionDetails = jdbcUrl.split("@//")[1];
                return username + "@" + connectionDetails;
            } catch (Exception e) {
                return username + "@" + jdbcUrl;
            }
        }
    }
}
