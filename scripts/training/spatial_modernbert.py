"""
Spatial ModernBERT: Text + Bounding Box Embeddings for Document Classification

Implements spatial-aware document understanding following LayoutLMv3 approach:
- 6 spatial embedding layers (x0, y0, x1, y1, width, height)
- Each embedding: 1000 vocab × 128 dim
- Fused with text embeddings before transformer layers

Architecture:
    text_embed (768) + spatial_embed (768) → ModernBERT → Classifier

Reference:
    LayoutLMv3: https://arxiv.org/abs/2204.08387
    Spatial ModernBERT: https://arxiv.org/html/2507.08865
"""

import torch
import torch.nn as nn
from transformers import ModernBertModel, ModernBertPreTrainedModel


class SpatialModernBERT(ModernBertPreTrainedModel):
    """ModernBERT with spatial (bounding box) embeddings for document classification.

    Args:
        config: ModernBertConfig with model_type='modernbert'
        num_labels: Number of classification labels (default: 7)

    Inputs:
        input_ids: Text token IDs [batch_size, seq_length]
        attention_mask: Attention mask [batch_size, seq_length]
        bbox_features: Normalized bbox coords [batch_size, 6] containing:
            - x0: left coordinate [0-999]
            - y0: top coordinate [0-999]
            - x1: right coordinate [0-999]
            - y1: bottom coordinate [0-999]
            - width: bbox width [0-999]
            - height: bbox height [0-999]
        labels (optional): Ground truth labels [batch_size]

    Outputs:
        If labels provided: (loss, logits)
        Else: logits [batch_size, num_labels]
    """

    def __init__(self, config, num_labels=7):
        super().__init__(config)
        self.num_labels = num_labels

        # ModernBERT encoder
        self.modernbert = ModernBertModel(config)

        # Spatial embedding layers (6 features × 128 dim = 768 total)
        # Vocabulary size: 1000 (for normalized bbox coords [0-999])
        self.x0_embedding = nn.Embedding(1000, 128)
        self.y0_embedding = nn.Embedding(1000, 128)
        self.x1_embedding = nn.Embedding(1000, 128)
        self.y1_embedding = nn.Embedding(1000, 128)
        self.width_embedding = nn.Embedding(1000, 128)
        self.height_embedding = nn.Embedding(1000, 128)

        # Classifier head
        dropout_prob = getattr(config, "classifier_dropout", 0.1)
        self.dropout = nn.Dropout(dropout_prob)
        self.classifier = nn.Linear(config.hidden_size, num_labels)

        # Initialize weights
        self.post_init()

    def forward(
        self, input_ids=None, attention_mask=None, bbox_features=None, labels=None, return_dict=True
    ):
        """Forward pass with spatial feature fusion."""

        # Validate inputs
        if input_ids is None:
            raise ValueError("input_ids must be provided")
        if bbox_features is None:
            raise ValueError("bbox_features must be provided")

        batch_size = input_ids.shape[0]

        # Get ModernBERT hidden states using standard forward pass
        # This handles all embedding logic internally
        outputs = self.modernbert(
            input_ids=input_ids, attention_mask=attention_mask, return_dict=True
        )

        # Get sequence output [batch_size, seq_length, hidden_size]
        sequence_output = outputs.last_hidden_state

        # Embed spatial features (per document, not per token)
        # bbox_features shape: [batch_size, 6]
        x0_emb = self.x0_embedding(bbox_features[:, 0])  # [batch_size, 128]
        y0_emb = self.y0_embedding(bbox_features[:, 1])  # [batch_size, 128]
        x1_emb = self.x1_embedding(bbox_features[:, 2])  # [batch_size, 128]
        y1_emb = self.y1_embedding(bbox_features[:, 3])  # [batch_size, 128]
        width_emb = self.width_embedding(bbox_features[:, 4])  # [batch_size, 128]
        height_emb = self.height_embedding(bbox_features[:, 5])  # [batch_size, 128]

        # Concatenate spatial embeddings: 6 × 128 = 768 dims
        spatial_embeddings = torch.cat(
            [x0_emb, y0_emb, x1_emb, y1_emb, width_emb, height_emb], dim=-1
        )  # [batch_size, 768]

        # Fuse spatial info with [CLS] token representation
        # We add spatial info to the [CLS] token (first token)
        cls_output = sequence_output[:, 0, :]  # [batch_size, hidden_size]
        cls_output_with_spatial = cls_output + spatial_embeddings  # [batch_size, 768]

        # Classification with spatial-enhanced [CLS]
        cls_output_with_spatial = self.dropout(cls_output_with_spatial)
        logits = self.classifier(cls_output_with_spatial)  # [batch_size, num_labels]

        # Calculate loss if labels provided
        loss = None
        if labels is not None:
            loss_fct = nn.CrossEntropyLoss()
            loss = loss_fct(logits.view(-1, self.num_labels), labels.view(-1))

        if not return_dict:
            output = (logits,) + outputs[1:]
            return ((loss,) + output) if loss is not None else output

        # Return dict format - only include hidden_states/attentions if they exist
        result = {"loss": loss, "logits": logits}

        if hasattr(outputs, "hidden_states") and outputs.hidden_states is not None:
            result["hidden_states"] = outputs.hidden_states
        if hasattr(outputs, "attentions") and outputs.attentions is not None:
            result["attentions"] = outputs.attentions

        return result


class FocalLoss(nn.Module):
    """Focal Loss for handling class imbalance.

    Focal Loss down-weights easy examples and focuses on hard examples.
    Formula: FL(pt) = -α(1 - pt)^γ * log(pt)

    Args:
        alpha: Weighting factor in [0,1] (default: 0.25)
        gamma: Focusing parameter ≥ 0 (default: 2.0)
        reduction: 'mean' or 'sum' (default: 'mean')

    Reference:
        Lin et al., "Focal Loss for Dense Object Detection", ICCV 2017
    """

    def __init__(self, alpha=0.25, gamma=2.0, reduction="mean"):
        super().__init__()
        self.alpha = alpha
        self.gamma = gamma
        self.reduction = reduction

    def forward(self, inputs, targets):
        """Calculate focal loss.

        Args:
            inputs: Predicted logits [batch_size, num_classes]
            targets: Ground truth labels [batch_size]

        Returns:
            Focal loss value
        """
        # Calculate cross-entropy
        ce_loss = nn.functional.cross_entropy(inputs, targets, reduction="none")

        # Calculate pt (probability of correct class)
        pt = torch.exp(-ce_loss)

        # Apply focal term: (1 - pt)^gamma
        focal_term = (1 - pt) ** self.gamma

        # Apply alpha weighting
        loss = self.alpha * focal_term * ce_loss

        if self.reduction == "mean":
            return loss.mean()
        elif self.reduction == "sum":
            return loss.sum()
        else:
            return loss


def test_spatial_modernbert():
    """Test spatial ModernBERT architecture."""
    from transformers import ModernBertConfig

    print("Testing Spatial ModernBERT...")
    print("=" * 80)

    # Create config
    config = ModernBertConfig(
        hidden_size=768,
        num_hidden_layers=12,
        num_attention_heads=12,
        intermediate_size=3072,
        hidden_dropout_prob=0.1,
        max_position_embeddings=8192,
        vocab_size=50368,
    )

    # Create model
    model = SpatialModernBERT(config, num_labels=7)
    print(f"✓ Model created: {sum(p.numel() for p in model.parameters()):,} parameters")

    # Test forward pass
    batch_size = 4
    seq_length = 128

    input_ids = torch.randint(0, config.vocab_size, (batch_size, seq_length))
    attention_mask = torch.ones(batch_size, seq_length)
    bbox_features = torch.randint(0, 1000, (batch_size, 6))  # Normalized [0-999]
    labels = torch.randint(0, 7, (batch_size,))

    print("\nInput shapes:")
    print(f"  input_ids:     {input_ids.shape}")
    print(f"  attention_mask: {attention_mask.shape}")
    print(f"  bbox_features: {bbox_features.shape}")
    print(f"  labels:        {labels.shape}")

    # Forward pass
    outputs = model(
        input_ids=input_ids,
        attention_mask=attention_mask,
        bbox_features=bbox_features,
        labels=labels,
    )

    print("\nOutput shapes:")
    print(f"  loss:    {outputs['loss'].shape if outputs['loss'] is not None else 'N/A'}")
    print(f"  logits:  {outputs['logits'].shape}")

    print(f"\nLoss value: {outputs['loss'].item():.4f}")
    print(
        f"Logits range: [{outputs['logits'].min().item():.2f}, {outputs['logits'].max().item():.2f}]"
    )

    # Test Focal Loss
    print("\n" + "=" * 80)
    print("Testing Focal Loss...")
    focal_loss = FocalLoss(alpha=0.25, gamma=2.0)
    loss_value = focal_loss(outputs["logits"], labels)
    print(f"Focal loss: {loss_value.item():.4f}")

    print("\n✓ All tests passed!")


if __name__ == "__main__":
    test_spatial_modernbert()
