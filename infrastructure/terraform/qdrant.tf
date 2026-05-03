# Self-hosted Qdrant on EC2.
#
# Why not managed: AWS does not offer Qdrant as a managed service, and
# Qdrant Cloud is a separate provider/contract. Per
# plans/05_cloud_deployment_strategy.md, the right answer for this stack
# is a single EC2 host with persistent EBS until vector volume justifies
# moving off-AWS.
#
# Storage shape: a separate gp3 EBS volume mounted at /qdrant/storage so
# the AMI can be replaced without touching the index.

# Latest Amazon Linux 2023 ARM64 AMI (matches t4g.* instance types).
data "aws_ami" "al2023_arm64" {
  most_recent = true
  owners      = ["137112412989"] # Amazon

  filter {
    name   = "name"
    values = ["al2023-ami-*-arm64"]
  }
  filter {
    name   = "state"
    values = ["available"]
  }
}

resource "aws_iam_role" "qdrant" {
  name               = "${local.name}-qdrant-instance"
  assume_role_policy = data.aws_iam_policy_document.ec2_assume.json
}

data "aws_iam_policy_document" "ec2_assume" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["ec2.amazonaws.com"]
    }
  }
}

# SSM access for shell-less administration.
resource "aws_iam_role_policy_attachment" "qdrant_ssm" {
  role       = aws_iam_role.qdrant.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
}

resource "aws_iam_instance_profile" "qdrant" {
  name = "${local.name}-qdrant-profile"
  role = aws_iam_role.qdrant.name
}

resource "aws_ebs_volume" "qdrant_data" {
  availability_zone = data.aws_availability_zones.available.names[0]
  size              = var.qdrant_volume_size
  type              = "gp3"
  encrypted         = true

  tags = { Name = "${local.name}-qdrant-data" }
}

# user_data: install Docker, format and mount the data volume on first
# boot, run qdrant under systemd. Idempotent — safe to re-run.
locals {
  qdrant_user_data = <<-EOT
    #!/bin/bash
    set -euxo pipefail

    dnf update -y
    dnf install -y docker
    systemctl enable --now docker

    DEVICE=/dev/sdf
    MOUNT=/qdrant/storage
    mkdir -p "$MOUNT"

    # Wait for the volume to attach, then format if it has no fs.
    until [ -e "$DEVICE" ]; do sleep 2; done
    if ! blkid "$DEVICE" >/dev/null 2>&1; then
        mkfs.ext4 -F "$DEVICE"
    fi
    if ! grep -q "$MOUNT" /etc/fstab; then
        echo "$DEVICE $MOUNT ext4 defaults,nofail 0 2" >> /etc/fstab
    fi
    mount -a

    cat > /etc/systemd/system/qdrant.service <<'UNIT'
    [Unit]
    Description=Qdrant vector DB
    After=docker.service
    Requires=docker.service

    [Service]
    Restart=always
    ExecStartPre=-/usr/bin/docker rm -f qdrant
    ExecStart=/usr/bin/docker run --rm --name qdrant \
        -p 6333:6333 \
        -v /qdrant/storage:/qdrant/storage \
        qdrant/qdrant:latest
    ExecStop=/usr/bin/docker stop qdrant

    [Install]
    WantedBy=multi-user.target
    UNIT

    systemctl daemon-reload
    systemctl enable --now qdrant
  EOT
}

resource "aws_instance" "qdrant" {
  ami                    = data.aws_ami.al2023_arm64.id
  instance_type          = var.qdrant_instance_type
  subnet_id              = aws_subnet.private[0].id
  vpc_security_group_ids = [aws_security_group.qdrant.id]
  iam_instance_profile   = aws_iam_instance_profile.qdrant.name
  user_data              = local.qdrant_user_data

  metadata_options {
    http_tokens   = "required" # IMDSv2 only
    http_endpoint = "enabled"
  }

  root_block_device {
    volume_size = 20
    volume_type = "gp3"
    encrypted   = true
  }

  tags = { Name = "${local.name}-qdrant" }
}

resource "aws_volume_attachment" "qdrant_data" {
  device_name = "/dev/sdf"
  volume_id   = aws_ebs_volume.qdrant_data.id
  instance_id = aws_instance.qdrant.id
}
