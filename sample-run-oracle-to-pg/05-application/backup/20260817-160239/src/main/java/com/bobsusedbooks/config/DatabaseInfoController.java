package com.bobsusedbooks.config;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.web.bind.annotation.ControllerAdvice;
import org.springframework.web.bind.annotation.ModelAttribute;

@ControllerAdvice
public class DatabaseInfoController {

    @Value("${spring.datasource.url}")
    private String datasourceUrl;

    @Value("${spring.datasource.username}")
    private String datasourceUsername;

    @ModelAttribute("databaseInfo")
    public String getDatabaseInfo() {
        try {
            // Format: jdbc:oracle:thin:@//localhost:1521/freepdb1
            String connectionDetails = datasourceUrl.split("@//")[1];
            return datasourceUsername + "@" + connectionDetails;
        } catch (Exception e) {
            return datasourceUsername + "@" + datasourceUrl;
        }
    }
}
