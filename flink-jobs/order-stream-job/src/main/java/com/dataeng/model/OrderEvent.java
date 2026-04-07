package com.dataeng.model;

import com.fasterxml.jackson.annotation.JsonProperty;

public class OrderEvent {

    @JsonProperty("order_id")
    private String orderId;

    private String status;

    private double amount;

    @JsonProperty("updated_at")
    private String updatedAt;

    // No-arg constructor (required by Jackson + Flink serialization)
    public OrderEvent() {}

    public String getOrderId() {
        return orderId;
    }

    public void setOrderId(String orderId) {
        this.orderId = orderId;
    }

    public String getStatus() {
        return status;
    }

    public void setStatus(String status) {
        this.status = status;
    }

    public double getAmount() {
        return amount;
    }

    public void setAmount(double amount) {
        this.amount = amount;
    }

    public String getUpdatedAt() {
        return updatedAt;
    }

    public void setUpdatedAt(String updatedAt) {
        this.updatedAt = updatedAt;
    }

    @Override
    public String toString() {
        return "OrderEvent{"
                + "orderId='" + orderId + '\''
                + ", status='" + status + '\''
                + ", amount=" + amount
                + ", updatedAt='" + updatedAt + '\''
                + '}';
    }
}
