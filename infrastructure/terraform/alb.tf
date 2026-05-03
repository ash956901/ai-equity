# ALB with two target groups:
#   api-tg       (port 8001) — receives /api/*, /auth/*, /healthz, /ready
#   frontend-tg  (port 80)   — receives everything else (default)

resource "aws_lb" "main" {
  name               = "${local.name}-alb"
  load_balancer_type = "application"
  internal           = false
  security_groups    = [aws_security_group.alb.id]
  subnets            = aws_subnet.public[*].id

  idle_timeout = 120 # accommodate long-running LLM responses on /chat
}

resource "aws_lb_target_group" "api" {
  name        = "${local.name}-api-tg"
  port        = 8001
  protocol    = "HTTP"
  vpc_id      = aws_vpc.main.id
  target_type = "ip" # required for Fargate awsvpc tasks

  health_check {
    enabled             = true
    path                = "/healthz"
    matcher             = "200"
    interval            = 15
    timeout             = 5
    healthy_threshold   = 2
    unhealthy_threshold = 3
  }

  deregistration_delay = 30
}

resource "aws_lb_target_group" "frontend" {
  name        = "${local.name}-fe-tg"
  port        = 80
  protocol    = "HTTP"
  vpc_id      = aws_vpc.main.id
  target_type = "ip"

  health_check {
    enabled             = true
    path                = "/healthz"
    matcher             = "200"
    interval            = 15
    timeout             = 5
    healthy_threshold   = 2
    unhealthy_threshold = 3
  }

  deregistration_delay = 30
}

# ACM cert + 443 listener — only when a domain is configured.
resource "aws_acm_certificate" "main" {
  count             = var.domain_name == "" ? 0 : 1
  domain_name       = var.domain_name
  validation_method = "DNS"

  lifecycle {
    create_before_destroy = true
  }
}

# HTTP:80 listener.
# Without a domain: terminates here, returns app traffic.
# With a domain: redirects to HTTPS.
resource "aws_lb_listener" "http" {
  load_balancer_arn = aws_lb.main.arn
  port              = 80
  protocol          = "HTTP"

  default_action {
    type = var.domain_name == "" ? "forward" : "redirect"

    dynamic "forward" {
      for_each = var.domain_name == "" ? [1] : []
      content {
        target_group {
          arn = aws_lb_target_group.frontend.arn
        }
      }
    }

    dynamic "redirect" {
      for_each = var.domain_name == "" ? [] : [1]
      content {
        protocol    = "HTTPS"
        port        = "443"
        status_code = "HTTP_301"
      }
    }
  }
}

# HTTPS:443 listener (domain-only).
resource "aws_lb_listener" "https" {
  count             = var.domain_name == "" ? 0 : 1
  load_balancer_arn = aws_lb.main.arn
  port              = 443
  protocol          = "HTTPS"
  ssl_policy        = "ELBSecurityPolicy-TLS13-1-2-2021-06"
  certificate_arn   = aws_acm_certificate.main[0].arn

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.frontend.arn
  }
}

# Listener rules — applied on whichever listener is active. Higher
# priority numbers evaluate later; we put the most specific paths first.
locals {
  active_listener_arn = var.domain_name == "" ? aws_lb_listener.http.arn : aws_lb_listener.https[0].arn
}

resource "aws_lb_listener_rule" "api_paths" {
  listener_arn = local.active_listener_arn
  priority     = 100

  action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.api.arn
  }

  condition {
    path_pattern {
      values = [
        "/api/*",
        "/auth/*",
        "/agent/*",
        "/agents/*",
        "/chat/*",
        "/healthz",
        "/ready",
        "/metrics",
        "/uploads/*",
        "/docs",
        "/openapi.json",
      ]
    }
  }
}
